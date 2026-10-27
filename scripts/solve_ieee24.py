"""Prepare or solve one source-identified IEEE24 sample with the author's B-theta UC.

No Python solver package is required. --prepare-only writes a readable LP and
metadata without starting COPT. A normal run invokes the installed COPT command
line, preserves its raw output and independently checks any complete candidate.
"""
import argparse
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from check_ieee24_solution import CASE_ID, check_candidate, load_case

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def var(kind, entity, period):
    return f'{kind}_{entity}_{period}'


@dataclass
class Row:
    name: str
    coefficients: dict
    sense: str
    rhs: float


@dataclass
class LinearModel:
    variables: dict = field(default_factory=dict)
    objective: dict = field(default_factory=dict)
    rows: list = field(default_factory=list)

    def variable(self, name, binary=False):
        if name in self.variables:
            raise ValueError('Duplicate variable: ' + name)
        # Pyomo source p/r/flow/theta are unrestricted Reals. Their relevant
        # nonnegative limits are explicitly generated as the author's rows.
        self.variables[name] = 'B' if binary else 'C'

    def row(self, name, terms, sense, rhs=0):
        coefficients = {}
        for variable, coefficient in terms:
            if variable not in self.variables:
                raise ValueError('Unknown variable: ' + variable)
            coefficients[variable] = coefficients.get(variable, 0) + coefficient
        coefficients = {key: float(value) for key, value in coefficients.items() if value != 0}
        if sense not in ('<=', '>=', '=') or not math.isfinite(rhs) or not all(math.isfinite(c) for c in coefficients.values()):
            raise ValueError('Invalid linear row: ' + name)
        self.rows.append(Row(name, coefficients, sense, float(rhs)))

    def expression(self, terms):
        text = []
        for name, coefficient in terms.items():
            if coefficient:
                text.append(('+' if coefficient > 0 else '-') + ' ' + format(abs(coefficient), '.17g') + ' ' + name)
        return ' '.join(text) if text else '0'

    def write_lp(self, path):
        lines = ['\\ Author Notebook cell 30, direct cyclic B-theta UC transcription',
                 'Minimize', ' obj: ' + self.expression(self.objective), 'Subject To']
        lines.extend(' ' + row.name + ': ' + self.expression(row.coefficients) + ' ' + row.sense + ' ' + format(row.rhs, '.17g') for row in self.rows)
        lines.append('Bounds')
        lines.extend(' ' + name + ' free' for name, kind in self.variables.items() if kind == 'C')
        lines.append('Binaries')
        lines.extend(' ' + name for name, kind in self.variables.items() if kind == 'B')
        lines.append('End')
        Path(path).write_text('\n'.join(lines) + '\n', encoding='ascii', newline='\n')

    def summary(self):
        return {'variables': len(self.variables), 'binaries': sum(v == 'B' for v in self.variables.values()),
                'continuous_free': sum(v == 'C' for v in self.variables.values()), 'constraints': len(self.rows),
                'constraint_groups': dict(Counter(row.name.rsplit('_', 2)[0] for row in self.rows)),
                'objective_nonzero_terms': sum(v != 0 for v in self.objective.values())}


def build_model(generators, branches, loads):
    """Return LinearModel; loads maps one-based bus IDs to period arrays.

    Row.coefficients is a variable-name -> coefficient dictionary and every row
    is in coefficients*x sense rhs form. No solver is called by this function.
    """
    buses = sorted(loads)
    if not buses or 1 not in buses:
        raise ValueError('The author reference bus 1 is required')
    horizon = len(loads[buses[0]])
    if horizon < 1 or any(len(loads[n]) != horizon or any(not math.isfinite(x) for x in loads[n]) for n in buses):
        raise ValueError('Invalid load arrays')
    gids = [g['genNo'] for g in generators]
    bids = [b['branchNo'] for b in branches]
    if len(gids) != len(set(gids)) or len(bids) != len(set(bids)):
        raise ValueError('Duplicate generator or branch IDs')
    model = LinearModel()
    for generator in generators:
        for t in range(1, horizon + 1):
            for kind in ('p', 'u', 'v', 'r'):
                model.variable(var(kind, generator['genNo'], t), binary=kind in ('u', 'v'))
    for branch in branches:
        for t in range(1, horizon + 1):
            model.variable(var('f', branch['branchNo'], t))
    for bus in buses:
        for t in range(1, horizon + 1):
            model.variable(var('theta', bus, t))
    wrap = lambda t: (t - 1) % horizon + 1
    for generator in generators:
        g = generator['genNo']
        if generator['genD_bus'] not in loads:
            raise ValueError('Unknown generator bus')
        up, down = generator['genD_minUP'], generator['genD_minDN']
        if type(up) is not int or type(down) is not int or not 1 <= up <= horizon or not 1 <= down <= horizon:
            raise ValueError('Author cyclic windows require integer minimum times within the horizon')
        for t in range(1, horizon + 1):
            prev = wrap(t - 1)
            p, u, v, r = (var(kind, g, t) for kind in ('p', 'u', 'v', 'r'))
            pp, uprev = var('p', g, prev), var('u', g, prev)
            for name, coefficient in ((p, generator['genC_Cost']), (u, generator['genC_NLoad']), (v, generator['genC_Startup'])):
                model.objective[name] = float(coefficient)
            model.row(f'pmin_{g}_{t}', [(p, 1), (u, -generator['genD_Pmin'])], '>=')
            model.row(f'pmax_{g}_{t}', [(p, 1), (r, 1), (u, -generator['genD_Pmax'])], '<=')
            model.row(f'reserve_limit_{g}_{t}', [(r, 1), (u, -generator['SPRamp'])], '<=')
            model.row(f'reserve_nonnegative_{g}_{t}', [(r, 1)], '>=')
            model.row(f'reserve_total_{g}_{t}', [(var('r', other, t), 1) for other in gids] + [(p, -1), (r, -1)], '>=')
            # Preserve the source's u-factor asymmetry:
            # hour1 uses u24; hours2..24 use current u_t. Do not "repair" it.
            ramp_u = uprev if t == 1 else u
            model.row(f'ramp_up_{g}_{t}', [(p, 1), (pp, -1), (ramp_u, -generator['HRamp']), (v, -generator['StartRamp'])], '<=')
            model.row(f'ramp_down_{g}_{t}', [(pp, 1), (p, -1), (u, generator['StartRamp'] - generator['HRamp']), (v, -generator['StartRamp']), (uprev, -generator['StartRamp'])], '<=')
            model.row(f'min_up_{g}_{t}', [(var('v', g, wrap(t - k)), 1) for k in range(up)] + [(u, -1)], '<=')
            model.row(f'min_down_{g}_{t}', [(var('v', g, wrap(t + k)), 1) for k in range(1, down + 1)] + [(u, 1)], '<=', 1)
            model.row(f'startup_{g}_{t}', [(v, 1), (u, -1), (uprev, 1)], '>=')
    for t in range(1, horizon + 1):
        model.row(f'slack_1_{t}', [(var('theta', 1, t), 1)], '=')
        for branch in branches:
            k, a, b = branch['branchNo'], branch['branch_fbus'], branch['branch_tbus']
            if a not in loads or b not in loads or a == b:
                raise ValueError('Invalid physical branch endpoints')
            flow = var('f', k, t)
            # Exactly the source equation, without an undocumented power/base change.
            model.row(f'dc_flow_{k}_{t}', [(var('theta', b, t), branch['branch_b']), (var('theta', a, t), -branch['branch_b']), (flow, -0.01)], '=')
            model.row(f'flow_min_{k}_{t}', [(flow, 1)], '>=', -branch['branch_rateA'])
            model.row(f'flow_max_{k}_{t}', [(flow, 1)], '<=', branch['branch_rateA'])
        for bus in buses:
            terms = [(var('p', g['genNo'], t), 1) for g in generators if g['genD_bus'] == bus]
            terms += [(var('f', b['branchNo'], t), 1) for b in branches if b['branch_tbus'] == bus]
            terms += [(var('f', b['branchNo'], t), -1) for b in branches if b['branch_fbus'] == bus]
            model.row(f'nodal_balance_{bus}_{t}', terms, '=', loads[bus][t - 1])
    return model


def copt_commands(time_limit=300.0, relative_gap=1e-4, threads=1, *, import_only=False):
    # COPT script text is ASCII. On Windows its command parser may interpret
    # UTF-8 Chinese path bytes using ANSI. subprocess cwd supplies the full path.
    commands = ['#COPT script file', 'cd .', 'read model.lp', 'get Rows', 'get Cols', 'get Bins']
    if import_only:
        return '\n'.join(commands + ['writelp imported.lp', 'quit']) + '\n'
    commands += [f'set TimeLimit {time_limit:.17g}', f'set RelGap {relative_gap:.17g}', f'set Threads {threads}',
                 # The source DC rows use flow/100. A 1e-6 row tolerance
                 # permits 1e-4 MW mismatch, larger than our 1e-5 MW checker.
                 'set FeasTol 1e-8', 'set IntTol 1e-8',
                 'set LogFile solver.log', 'writeparam effective_parameters.par', 'opt',
                 'get Status', 'get HasSol', 'get BestObj', 'get BestBnd', 'get BestGap', 'get SolvingTime',
                 'writemst solution.mst', 'quit']
    return '\n'.join(commands) + '\n'


def decode_console(data):
    for encoding in ('utf-8', 'gb18030'):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return data.decode('utf-8', errors='replace'), 'utf-8-with-replacement'


def parse_console(text):
    integers = re.findall(r'IntAttr:\s*\[Current\]\s*([+-]?\d+)', text)
    doubles = re.findall(r'DblAttr:\s*\[Current\]\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)', text)
    if len(integers) != 5 or len(doubles) != 4:
        raise ValueError(f'Unexpected COPT attribute response counts: int={len(integers)}, double={len(doubles)}; inspect solver_console.txt')
    attrs = dict(zip(('Rows', 'Cols', 'Bins', 'Status', 'HasSol'), map(int, integers)))
    attrs.update(dict(zip(('BestObj', 'BestBnd', 'BestGap', 'SolvingTime'), map(float, doubles))))
    if not all(math.isfinite(attrs[key]) for key in ('BestObj', 'BestBnd', 'BestGap', 'SolvingTime')):
        raise ValueError('Non-finite COPT attribute response')
    version = re.search(r'Cardinal Optimizer v([^\r\n]+)', text)
    attrs['version'] = version.group(1).strip() if version else 'unknown; see raw console'
    return attrs


def parse_solution(path, expected_names):
    values, reported = {}, None
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith('#'):
            match = re.search(r'Objective\s+value\s*=?\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)', text, re.I)
            if match:
                reported = float(match.group(1))
            continue
        parts = text.split()
        if len(parts) != 2 or parts[0] not in expected_names or parts[0] in values:
            raise ValueError('Unexpected/duplicate candidate variable line: ' + text)
        value = float(parts[1])
        if not math.isfinite(value):
            raise ValueError('Non-finite solution variable')
        values[parts[0]] = value
    missing = sorted(set(expected_names) - values.keys())
    if missing:
        raise ValueError(f'Incomplete candidate: {len(missing)} missing variables; zeros are not silently inferred')
    if reported is not None and not math.isfinite(reported):
        raise ValueError('Non-finite candidate objective')
    return values, reported


def parse_numeric_parameters(path):
    parameters = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        parts = line.split()
        if len(parts) == 2 and not parts[0].startswith('#'):
            try:
                value = float(parts[1])
            except ValueError:
                continue
            if not math.isfinite(value):
                raise ValueError('Non-finite effective solver parameter')
            parameters[parts[0]] = value
    return parameters


def find_copt(explicit=None):
    candidates = [explicit, shutil.which('copt_cmd')]
    if os.getenv('COPT_HOME'):
        candidates.append(str(Path(os.environ['COPT_HOME']) / 'bin' / ('copt_cmd.exe' if os.name == 'nt' else 'copt_cmd')))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise FileNotFoundError('COPT command line not found; specify --copt-command or configure COPT_HOME/PATH')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample-id', type=int, default=1, help='One-based original demand row (default1)')
    parser.add_argument('--case-dir', type=Path, default=ROOT / 'cases' / CASE_ID)
    parser.add_argument('--output-dir', type=Path, help='New/empty run folder; default is a timestamped runs directory')
    parser.add_argument('--prepare-only', action='store_true', help='Write model/metadata only; never call a solver')
    parser.add_argument('--time-limit', type=float, default=300.0, help='COPT limit in seconds')
    parser.add_argument('--relative-gap', type=float, default=1e-4, help='COPT relative gap stopping parameter')
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--copt-command', help='Installed COPT command line executable')
    args = parser.parse_args(argv)
    if not math.isfinite(args.time_limit) or args.time_limit <= 0 or not math.isfinite(args.relative_gap) or not 0 <= args.relative_gap <= 1 or args.threads < 1:
        parser.error('Require positive finite time limit, 0<=relative_gap<=1 and positive thread count')
    now = datetime.now(timezone.utc)
    out = (args.output_dir or ROOT / 'runs' / CASE_ID / f'sample_{args.sample_id:04d}' / now.strftime('%Y%m%dT%H%M%S.%fZ')).resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Run output directory must be new/empty; old results are never overwritten')
    out.mkdir(parents=True, exist_ok=True)
    record = {'case_id': CASE_ID, 'sample_id': args.sample_id, 'created_utc': now.isoformat(),
              'status': 'preparing', 'solve_status': 'not_run', 'independent_solution_check': 'not_run',
              'output_dir': str(out), 'source_formulation': 'Notebook cell30 cyclic B-theta UC',
              'adapter_sha256': sha(Path(__file__)), 'independent_checker_sha256': sha(Path(__file__).with_name('check_ieee24_solution.py')),
              'environment': {'python': sys.version.split()[0], 'platform': sys.platform,
                              'windows_version': list(sys.getwindowsversion()) if hasattr(sys, 'getwindowsversion') else None,
                              'logical_cpu_count': os.cpu_count()},
              'requested_solver_parameters': {'TimeLimit': args.time_limit, 'RelGap': args.relative_gap,
                                              'Threads': args.threads, 'FeasTol': 1e-8, 'IntTol': 1e-8},
              'no_model_changes': ['38 physical branches retained', 'author per-generator reserve rule retained', '24-to1 cycle retained', 'source hour1 ramp factor retained', 'no load slack or invented initial history', 'G7 not fixed/deleted'],
              'publication_status': 'unpublished'}
    try:
        generators, branches, loads, identities = load_case(args.case_dir, args.sample_id)
        record['input_identity'] = identities
        model = build_model(generators, branches, loads)
        model.write_lp(out / 'model.lp')
        record['model'] = model.summary()
        record['model_lp_sha256'] = sha(out / 'model.lp')
        (out / 'solver_commands.txt').write_text(copt_commands(args.time_limit, args.relative_gap, args.threads), encoding='ascii', newline='\n')
        record['solver_command_script_sha256'] = sha(out / 'solver_commands.txt')
        if args.prepare_only:
            record['status'] = 'prepared_model_not_solved'
            write_json(out / 'run.json', record)
            print(json.dumps({'status': record['status'], 'sample_id': args.sample_id, **record['model'], 'run': str(out / 'run.json')}, ensure_ascii=False))
            return 0
        executable = find_copt(args.copt_command)
        record['solver_executable'] = executable
        record['solver_executable_sha256'] = sha(executable)
        record['status'] = 'solver_running'
        write_json(out / 'run.json', record)
        print(f'COPT: original sample {args.sample_id}; TimeLimit={args.time_limit}s, RelGap={args.relative_gap}, Threads={args.threads}. Output: {out}', flush=True)
        started = time.monotonic()
        completed = subprocess.run([executable, '-i', 'solver_commands.txt'], cwd=out, input=b'',
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=args.time_limit + 120)
        record['wall_time_seconds'] = time.monotonic() - started
        (out / 'solver_console.txt').write_bytes(completed.stdout)
        text, encoding = decode_console(completed.stdout)
        record['console_encoding'] = encoding
        record['process_exit_code'] = completed.returncode
        if completed.returncode != 0:
            raise RuntimeError('COPT command line returned nonzero; see solver_console.txt (check installed license/account)')
        attributes = parse_console(text)
        record['solver_attributes'] = attributes
        effective = parse_numeric_parameters(out / 'effective_parameters.par')
        record['effective_parameter_overrides'] = effective
        if any(effective.get(name) != 1e-8 for name in ('FeasTol', 'IntTol')):
            raise ValueError('COPT did not confirm the requested feasibility/integrality tolerances')
        expected = record['model']
        if (attributes['Rows'], attributes['Cols'], attributes['Bins']) != (expected['constraints'], expected['variables'], expected['binaries']):
            raise ValueError('COPT imported model dimensions differ from the generated model')
        record['solve_status'] = 'solver_returned'
        status, has_solution = attributes['Status'], attributes['HasSol']
        if has_solution not in (0, 1):
            raise ValueError('Invalid HasSol value')
        record['solver_reported_status_code'] = status
        record['has_candidate'] = bool(has_solution)
        record['objective_value'] = attributes['BestObj'] if has_solution else None
        record['best_bound'] = attributes['BestBnd'] if abs(attributes['BestBnd']) < 1e29 else None
        record['relative_gap'] = attributes['BestGap'] if has_solution else None
        record['solver_time_seconds'] = attributes['SolvingTime']
        if status == 1 and (not has_solution or record['best_bound'] is None):
            raise ValueError('Optimal status lacks a candidate or finite useful bound')
        if has_solution:
            values, solution_header_obj = parse_solution(out / 'solution.mst', set(model.variables))
            if solution_header_obj is not None and abs(solution_header_obj - attributes['BestObj']) > 1e-4 + 1e-8 * abs(attributes['BestObj']):
                raise ValueError('Raw candidate objective and COPT reported objective differ')
            candidate = {'case_id': CASE_ID, 'sample_id': args.sample_id, 'objective_value': attributes['BestObj'],
                         'input_identity': identities, 'raw_solution_sha256': sha(out / 'solution.mst'), 'values': values}
            write_json(out / 'solution_values.json', candidate)
            checked = check_candidate(generators, branches, loads, values, objective_value=attributes['BestObj'])
            checked.update({'case_id': CASE_ID, 'sample_id': args.sample_id, 'solution_sha256': sha(out / 'solution_values.json'), 'checker_sha256': record['independent_checker_sha256']})
            write_json(out / 'independent_check.json', checked)
            record['independent_solution_check'] = checked['status']
            if not checked['passed']:
                record['status'] = 'candidate_rejected_by_independent_check'
                write_json(out / 'run.json', record)
                print(json.dumps({'status': record['status'], 'sample_id': args.sample_id, 'run': str(out / 'run.json')}, ensure_ascii=False))
                return 2
            record['status'] = 'optimal_within_declared_solver_tolerances' if status == 1 else 'feasible_not_proven_optimal'
        else:
            record['status'] = {0: 'not_started_or_run_error', 2: 'solver_reported_infeasible', 3: 'solver_reported_unbounded', 4: 'solver_reported_infeasible_or_unbounded', 8: 'time_limit_no_incumbent'}.get(status, 'solver_stopped_without_candidate')
        record['optimality_note'] = 'Solver status1 is relative to declared solver tolerances/RelGap; independent checker establishes candidate feasibility only.'
        record['file_sha256'] = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != 'run.json'}
        write_json(out / 'run.json', record)
        print(json.dumps({'status': record['status'], 'sample_id': args.sample_id, 'objective_value': record['objective_value'], 'best_bound': record['best_bound'], 'relative_gap': record['relative_gap'], 'independent_solution_check': record['independent_solution_check'], 'run': str(out / 'run.json')}, ensure_ascii=False))
        return 0 if has_solution or status == 2 else 1
    except KeyboardInterrupt:
        record.update({'status': 'interrupted_by_user', 'solve_status': 'interrupted'})
        write_json(out / 'run.json', record)
        print(json.dumps({'status': record['status'], 'run': str(out / 'run.json')}, ensure_ascii=False))
        return 130
    except Exception as exc:
        if isinstance(exc, subprocess.TimeoutExpired) and exc.stdout:
            (out / 'solver_console.txt').write_bytes(exc.stdout)
        record.update({'status': 'run_error', 'error_type': type(exc).__name__, 'error': str(exc)})
        write_json(out / 'run.json', record)
        print(json.dumps({'status': 'run_error', 'error': str(exc), 'run': str(out / 'run.json')}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
