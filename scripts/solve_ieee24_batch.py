"""Solve independent IEEE24 samples, resume verified runs and preserve all outcomes.

Each worker invokes the already reviewed single-sample entry. No model, source
data or numerical settings are altered. No network or publication is performed.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from check_ieee24_solution import CASE_ID, load_case, load_json

ROOT = Path(__file__).resolve().parents[1]
SINGLE = ROOT / 'scripts/solve_ieee24.py'
CHECKER = ROOT / 'scripts/check_ieee24_solution.py'
TERMINAL = {'optimal_within_declared_solver_tolerances', 'feasible_not_proven_optimal',
            'solver_reported_infeasible', 'solver_reported_unbounded',
            'solver_reported_infeasible_or_unbounded', 'time_limit_no_incumbent',
            'solver_stopped_without_candidate'}
FIELDS = ['sample_id', 'status', 'has_candidate', 'independent_status', 'objective_value',
          'best_bound', 'relative_gap', 'solver_seconds', 'wall_seconds', 'generation_cost',
          'no_load_cost', 'startup_cost', 'independent_failing_evaluations', 'max_MW_violation',
          'max_binary_distance', 'objective_recompute_abs_error', 'reused_existing_run', 'run_json', 'error']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def reusable_run(path, sample_id, expected):
    """Return a trusted terminal record, or None; never repair existing files."""
    try:
        record = load_json(path)
        if record.get('case_id') != CASE_ID or record.get('sample_id') != sample_id or record.get('status') not in TERMINAL:
            return None
        if record.get('adapter_sha256') != expected['adapter'] or record.get('independent_checker_sha256') != expected['checker']:
            return None
        if record.get('requested_solver_parameters') != expected['parameters']:
            return None
        identity = record.get('input_identity', {})
        if identity.get('sample_id') != sample_id or identity.get('input_sha256') != expected['input'] or identity.get('source_sha256') != expected['source']:
            return None
        if not record.get('file_sha256'):
            return None
        required = {'model.lp', 'solver_commands.txt', 'solver_console.txt',
                    'effective_parameters.par', 'solver.log'}
        if not required.issubset(record['file_sha256']):
            return None
        if record['status'] in {'optimal_within_declared_solver_tolerances', 'feasible_not_proven_optimal'} and record.get('has_candidate') is not True:
            return None
        folder = Path(path).parent.resolve()
        for name, digest in record['file_sha256'].items():
            target = (folder / name).resolve()
            if target.parent != folder or sha(target) != digest:
                return None
        if record.get('has_candidate'):
            required = {'solution_values.json', 'solution.mst', 'independent_check.json', 'model.lp'}
            if not required.issubset(record['file_sha256']):
                return None
            checked = load_json(folder / 'independent_check.json')
            if checked.get('passed') is not True or checked.get('status') != 'feasible_within_declared_tolerances':
                return None
        return record
    except (OSError, ValueError, TypeError, KeyError):
        return None


def row_from_run(path, *, reused=False):
    record = load_json(path)
    folder = Path(path).parent
    row = {key: None for key in FIELDS}
    row.update({'sample_id': record['sample_id'], 'status': record['status'],
                'has_candidate': bool(record.get('has_candidate', False)),
                'independent_status': record.get('independent_solution_check', 'not_run'),
                'objective_value': record.get('objective_value'), 'best_bound': record.get('best_bound'),
                'relative_gap': record.get('relative_gap'), 'solver_seconds': record.get('solver_time_seconds'),
                'wall_seconds': record.get('wall_time_seconds'), 'reused_existing_run': reused,
                'run_json': str(Path(path).resolve().relative_to(ROOT)), 'error': record.get('error', '')})
    for name in ('objective_value', 'best_bound', 'relative_gap', 'solver_seconds', 'wall_seconds'):
        if row[name] is not None and (isinstance(row[name], bool) or not math.isfinite(row[name])):
            raise ValueError('Non-finite result field: ' + name)
    if (folder / 'independent_check.json').exists():
        checked = load_json(folder / 'independent_check.json')
        groups = checked.get('constraint_groups', {})
        objective = checked.get('objective', {})
        components = objective.get('components', {})
        row.update({'generation_cost': components.get('generation'), 'no_load_cost': components.get('no_load'),
                    'startup_cost': components.get('startup'), 'independent_failing_evaluations': checked.get('failing_evaluations'),
                    'max_MW_violation': max((g['max_violation'] for name, g in groups.items()
                                             if name not in {'binary_variables', 'reference_angle', 'cyclic_minimum_up', 'cyclic_minimum_down', 'startup_lower_bound', 'reported_objective'}), default=None),
                    'max_binary_distance': groups.get('binary_variables', {}).get('max_violation'),
                    'objective_recompute_abs_error': abs(objective['recomputed'] - record['objective_value'])
                        if objective.get('recomputed') is not None and record.get('objective_value') is not None else None})
    return row


def verified(row):
    return row.get('has_candidate') is True and row.get('independent_status') == 'feasible_within_declared_tolerances' and row.get('independent_failing_evaluations') == 0


def solve_worker(sample_id, batch_id, args, batch_folder):
    folder = ROOT / 'runs' / CASE_ID / f'sample_{sample_id:04d}' / batch_id
    command = [sys.executable, str(SINGLE), '--sample-id', str(sample_id), '--output-dir', str(folder),
               '--time-limit', str(args.time_limit), '--relative-gap', str(args.relative_gap), '--threads', str(args.threads)]
    try:
        process = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=args.time_limit + 180,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        path = folder / 'run.json'
        if path.exists():
            row = row_from_run(path)
        else:
            row = {key: None for key in FIELDS}
            row.update({'sample_id': sample_id, 'status': 'driver_error', 'has_candidate': False,
                        'independent_status': 'not_run', 'error': 'Single entry returned without run.json'})
        if process.returncode or row['status'] not in TERMINAL:
            logs = batch_folder / 'driver_errors'
            logs.mkdir(exist_ok=True)
            (logs / f'sample_{sample_id:04d}.txt').write_bytes(process.stdout)
            row['error'] = row.get('error') or f'Single entry exit code {process.returncode}'
        return row
    except Exception as exc:
        return {**{key: None for key in FIELDS}, 'sample_id': sample_id, 'status': 'driver_error',
                'has_candidate': False, 'independent_status': 'not_run',
                'error': type(exc).__name__ + ': ' + str(exc)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-id', type=int, default=1)
    parser.add_argument('--end-id', type=int, default=1800)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--time-limit', type=float, default=300)
    parser.add_argument('--relative-gap', type=float, default=1e-4)
    args = parser.parse_args(argv)
    if not (1 <= args.start_id <= args.end_id <= 1800 and 1 <= args.workers <= 12 and args.threads >= 1):
        parser.error('Invalid sample range or worker/thread count')
    if not math.isfinite(args.time_limit) or args.time_limit <= 0 or not math.isfinite(args.relative_gap) or not 0 <= args.relative_gap <= 1:
        parser.error('Invalid time limit/gap')
    _, _, _, identity = load_case(ROOT / 'cases' / CASE_ID, args.start_id)
    expected = {'adapter': sha(SINGLE), 'checker': sha(CHECKER), 'input': identity['input_sha256'],
                'source': identity['source_sha256'],
                'parameters': {'TimeLimit': args.time_limit, 'RelGap': args.relative_gap, 'Threads': args.threads,
                               'FeasTol': 1e-8, 'IntTol': 1e-8}}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    batch_id = 'batch_' + stamp
    folder = ROOT / 'runs' / CASE_ID / '_batches' / batch_id
    folder.mkdir(parents=True, exist_ok=False)
    requested = list(range(args.start_id, args.end_id + 1))
    rows, pending = {}, []
    for sample_id in requested:
        previous = sorted((ROOT / 'runs' / CASE_ID / f'sample_{sample_id:04d}').glob('*/run.json'), reverse=True)
        match = next((p for p in previous if reusable_run(p, sample_id, expected) is not None), None)
        if match is not None:
            rows[sample_id] = row_from_run(match, reused=True)
        else:
            pending.append(sample_id)
    state = {'batch_id': batch_id, 'case_id': CASE_ID, 'publication_status': 'unpublished',
             'created_utc': datetime.now(timezone.utc).isoformat(), 'status': 'running',
             'requested_sample_count': len(requested), 'requested_range': [args.start_id, args.end_id],
             'reused_existing_count': len(rows), 'newly_scheduled_count': len(pending),
             'workers': args.workers, 'parameters_per_sample': expected['parameters'],
             'batch_script_sha256': sha(Path(__file__)), 'input_identity': expected,
             'results_csv': str(folder / 'summary.csv')}
    started = time.monotonic()

    def checkpoint(active=()):
        state.update({'updated_utc': datetime.now(timezone.utc).isoformat(), 'wall_seconds': time.monotonic() - started,
                      'completed_or_attempted_count': len(rows), 'verified_candidate_count': sum(verified(r) for r in rows.values()),
                      'pending_count': len(requested) - len(rows), 'active_sample_ids': sorted(active),
                      'status_counts': dict(Counter(r['status'] for r in rows.values()))})
        atomic_json(folder / 'progress.json', state)
        temporary = folder / 'summary.csv.tmp'
        with temporary.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows[s] for s in sorted(rows))
        temporary.replace(folder / 'summary.csv')

    checkpoint()
    print(json.dumps({'batch_id': batch_id, 'reused': len(rows), 'pending': len(pending),
                      'workers': args.workers, 'progress': str(folder / 'progress.json')}, ensure_ascii=False), flush=True)
    iterator = iter(pending)
    pool = ThreadPoolExecutor(max_workers=args.workers)
    active = {}
    try:
        consecutive_errors = 0
        stop_scheduling = False
        def submit():
            if stop_scheduling:
                return
            sample_id = next(iterator, None)
            if sample_id is not None:
                active[pool.submit(solve_worker, sample_id, batch_id, args, folder)] = sample_id
        for _ in range(args.workers):
            submit()
        last_print = len(rows)
        while active:
            finished, _ = wait(active, timeout=5, return_when=FIRST_COMPLETED)
            for future in finished:
                sample_id = active.pop(future)
                rows[sample_id] = future.result()
                if rows[sample_id]['status'] not in TERMINAL:
                    consecutive_errors += 1
                else:
                    consecutive_errors = 0
                if consecutive_errors >= max(4, 2 * args.workers):
                    stop_scheduling = True
                submit()
            checkpoint(active.values())
            if len(rows) - last_print >= 25 or not active:
                print(json.dumps({'completed': len(rows), 'total': len(requested),
                                  'verified': state['verified_candidate_count'], 'counts': state['status_counts']}, ensure_ascii=True), flush=True)
                last_print = len(rows)
        state['status'] = ('stopped_on_repeated_run_errors' if stop_scheduling else
                           'completed' if all(r['status'] in TERMINAL for r in rows.values()) else 'completed_with_errors')
        checkpoint()
        print(json.dumps({'status': state['status'], 'completed': len(rows), 'verified': state['verified_candidate_count'],
                          'summary': str(folder / 'summary.csv'), 'progress': str(folder / 'progress.json')}, ensure_ascii=False), flush=True)
        return 0 if state['status'] == 'completed' else 1
    except KeyboardInterrupt:
        state['status'] = 'interrupted'
        checkpoint(active.values())
        pool.shutdown(wait=True, cancel_futures=True)
        return 130
    finally:
        pool.shutdown(wait=True, cancel_futures=True)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
