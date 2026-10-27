"""Package completed batch results and compare all normalized inputs to originals.

No solver is called. Error/no-candidate cases stay in summary.csv; only verified
complete candidates enter solutions.jsonl.gz. Detailed raw runs are retained.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile

from check_ieee24_solution import CASE_ID, load_json, expected_variables
from solve_ieee24_batch import reusable_run, row_from_run, sha, atomic_json, FIELDS

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
CASE = ROOT / 'cases' / CASE_ID
AUX = PROJECT / 'UC_dataset/learning/辅助材料/ieee24_rpglab/batch_results'


@contextmanager
def compressed_writer(path):
    with path.open('wb') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0, compresslevel=9) as compressed:
            yield compressed


def compare_inputs(expected):
    p = load_json(CASE / 'provenance.json')
    originals = {}
    identities = {}
    for entry in p['source']['files']:
        path = ROOT / entry['archive_path']
        encoded = path.read_bytes()
        data = gzip.decompress(encoded) if entry['original_name'] == 'demand24Bus.txt' else encoded
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry['original_sha256'] or sha(path) != entry['archive_sha256']:
            raise ValueError('Original source identity changed: ' + entry['original_name'])
        originals[entry['original_name']] = data
        identities[entry['original_name']] = digest
    if identities != expected['source']:
        raise ValueError('Batch source identities do not match current originals')
    for name, digest in expected['input'].items():
        if sha(CASE / name) != digest:
            raise ValueError('Normalized input changed during batch: ' + name)
    for relative, digest in {**p['artifact_sha256'], **p.get('profile_artifact_sha256', {})}.items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha(path) != digest:
            raise ValueError('Input/shared documentation identity changed: ' + relative)
    counts = {}
    for name, target in [('GenData_1GPerBus.dat', 'generators.json'), ('dataFileTxInfo24Bus.dat', 'branches.json')]:
        source_rows = list(csv.DictReader(io.StringIO(originals[name].decode('utf-8-sig'))))
        rows = load_json(CASE / target)
        if len(rows) != len(source_rows):
            raise ValueError('Original/normalized table row count differs')
        count = 0
        for source, converted in zip(source_rows, rows):
            if set(source) != set(converted) or any(Decimal(v.strip()) != Decimal(str(converted[k])) for k, v in source.items()):
                raise ValueError('Original table value differs: ' + name)
            count += len(source)
        counts[target] = count
    raw_rows = list(csv.reader(io.StringIO(originals['demand24Bus.txt'].decode('utf-8-sig'))))
    with gzip.open(CASE / 'demand_wide.csv.gz', 'rt', encoding='utf-8', newline='') as stream:
        rows = csv.reader(stream)
        header = next(rows)
        if header != ['sample_id'] + [f't{t:02d}_bus{b:02d}' for t in range(1, 25) for b in range(1, 25)]:
            raise ValueError('Normalized load column mapping differs')
        metrics = {}
        count = 0
        for index, (source, converted) in enumerate(zip(raw_rows, rows), start=1):
            if len(source) != 576 or len(converted) != 577 or converted[0] != str(index) or converted[1:] != [v.strip() for v in source]:
                raise ValueError('Load token/sample ordering differs at sample ' + str(index))
            totals = [math.fsum(float(x) for x in source[t * 24:(t + 1) * 24]) for t in range(24)]
            metrics[index] = {'peak_load_MW': max(totals), 'min_load_MW': min(totals), 'energy_MWh': math.fsum(totals)}
            count += 576
        if count != 1036800 or len(raw_rows) != 1800 or next(rows, None) is not None:
            raise ValueError('Load source/target lengths are incomplete')
    return {'all_original_and_normalized_numeric_values_preserved': True,
            'original_source_sha256': identities, 'normalized_input_sha256': expected['input'],
            'generator_numeric_values_compared': counts['generators.json'],
            'branch_numeric_values_compared': counts['branches.json'], 'load_tokens_compared': count,
            'sample_ids_and_time_bus_order_preserved': True,
            'changes': ['Original numeric values and author model rules retained.',
                        'Tables encoded as JSON; loads gained header/sample_id and reversible gzip compression.',
                        'New optimization/verification outputs are separate from inputs.']}, metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-dir', type=Path, required=True)
    args = parser.parse_args()
    folder = args.batch_dir.resolve()
    state = load_json(folder / 'progress.json')
    if state['status'] not in {'completed', 'completed_with_errors'} or state['pending_count'] != 0:
        raise ValueError('Batch is not complete; refuse to publish a final-looking result package')
    with (folder / 'summary.csv').open(encoding='utf-8-sig', newline='') as stream:
        source_rows = list(csv.DictReader(stream))
    ids = [int(x['sample_id']) for x in source_rows]
    wanted = list(range(state['requested_range'][0], state['requested_range'][1] + 1))
    if ids != wanted or len(ids) != len(set(ids)):
        raise ValueError('Batch summary misses or duplicates requested sample IDs')
    comparison, metrics = compare_inputs(state['input_identity'])
    final_output = ROOT / 'results' / CASE_ID / state['batch_id']
    if final_output.exists():
        raise ValueError('Refuse to overwrite an existing result package')
    final_output.parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='.building_' + state['batch_id'] + '_', dir=final_output.parent))
    AUX.mkdir(parents=True, exist_ok=True)
    generators = load_json(CASE / 'generators.json')
    branches = load_json(CASE / 'branches.json')
    required = set(expected_variables(generators, branches, range(1, 25), 24))
    rows, verified_ids, raw_hashes, solution_hashes = [], [], {}, {}
    total_independent_evaluations = 0
    examples = {}
    with compressed_writer(output / 'solutions.jsonl.gz') as gz:
        for source in source_rows:
            sid = int(source['sample_id'])
            row = dict(source)
            row.update({'sample_id': sid, **metrics[sid]})
            path = ROOT / source['run_json']
            record = load_json(path)
            if record['status'] != source['status'] or record['sample_id'] != sid:
                raise ValueError('Result summary and actual run differ')
            actual_row = row_from_run(path, reused=source['reused_existing_run'] == 'True')
            for key in FIELDS:
                expected_text = '' if actual_row[key] is None else str(actual_row[key])
                if source[key] != expected_text:
                    raise ValueError(f'Summary field differs from saved evidence: sample {sid}, {key}')
            raw_hashes[str(sid)] = {'run_json': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)}
            if record['status'] in {'optimal_within_declared_solver_tolerances', 'feasible_not_proven_optimal'} and record.get('has_candidate') and record.get('independent_solution_check') == 'feasible_within_declared_tolerances':
                if reusable_run(path, sid, state['input_identity']) is None:
                    raise ValueError('Candidate/source/hash evidence cannot be verified at sample ' + str(sid))
                candidate_path = path.parent / 'solution_values.json'
                candidate = load_json(candidate_path)
                checked = load_json(path.parent / 'independent_check.json')
                values = candidate['values']
                if set(values) != required or not all(type(x) in (int, float) and math.isfinite(x) for x in values.values()):
                    raise ValueError('Incomplete/non-finite normalized candidate')
                if not checked['passed'] or checked['failing_evaluations'] != 0:
                    raise ValueError('Candidate is not independently verified')
                total_independent_evaluations += checked['constraint_evaluations']
                payload = {'case_id': CASE_ID, 'sample_id': sid, 'status': record['status'],
                           'objective_value': record['objective_value'], 'best_bound': record['best_bound'],
                           'relative_gap': record['relative_gap'], 'values': values,
                           'source_run': path.relative_to(ROOT).as_posix(), 'source_solution_sha256': sha(candidate_path)}
                gz.write((json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8'))
                verified_ids.append(sid)
                solution_hashes[str(sid)] = sha(candidate_path)
                if sid == 1:
                    examples['sample1'] = {'run': record, 'values': values, 'check': checked}
            rows.append(row)
    # Independently re-open the compressed export and compare every variable
    # value to the corresponding saved candidate; no rounding is permitted.
    roundtrip = []
    with gzip.open(output / 'solutions.jsonl.gz', 'rt', encoding='utf-8') as stream:
        for line in stream:
            exported = json.loads(line)
            sid = exported['sample_id']
            source = load_json((ROOT / raw_hashes[str(sid)]['run_json']).parent / 'solution_values.json')
            if exported['values'] != source['values'] or exported['objective_value'] != source['objective_value']:
                raise ValueError('Compressed candidate roundtrip differs')
            roundtrip.append(sid)
    if roundtrip != verified_ids:
        raise ValueError('Compressed candidate IDs differ')
    with (output / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS + ['peak_load_MW', 'min_load_MW', 'energy_MWh'])
        writer.writeheader()
        writer.writerows(rows)
    statuses = dict(Counter(x['status'] for x in rows))
    good = [x for x in rows if x['sample_id'] in set(verified_ids)]
    number = lambda row, key: float(row[key]) if row.get(key) not in (None, '') else None
    statistics = {'requested_samples': len(ids), 'attempted_samples': len(rows), 'verified_candidates': len(good),
                  'without_verified_candidate_ids': [sid for sid in ids if sid not in set(verified_ids)],
                  'status_counts': statuses, 'variables_per_candidate': len(required),
                  'compressed_candidate_values_checked': len(required) * len(good),
                  'independent_constraint_and_objective_evaluations': total_independent_evaluations,
                  'target_relative_gap': state['parameters_per_sample']['RelGap'],
                  'gap_target_met_candidates': sum(number(x, 'relative_gap') is not None and number(x, 'relative_gap') <= state['parameters_per_sample']['RelGap'] + 1e-12 for x in good),
                  'batch_wall_seconds': state['wall_seconds'],
                  'sum_solver_seconds_including_reused': sum(number(x, 'solver_seconds') or 0 for x in rows),
                  'max_MW_violation': max((number(x, 'max_MW_violation') or 0 for x in good), default=None),
                  'max_binary_distance': max((number(x, 'max_binary_distance') or 0 for x in good), default=None),
                  'objective_min': min((number(x, 'objective_value') for x in good), default=None),
                  'objective_max': max((number(x, 'objective_value') for x in good), default=None),
                  'max_relative_gap': max((number(x, 'relative_gap') for x in good), default=None)}
    readme = f'''# IEEE24全量求解结果（本地，未上传）

对应原模型输入`rpglab_ieee24_native_v1`；{len(ids)}个独立24小时负荷样本，{len(good)}个候选通过独立验解。状态统计以provenance和summary为准，不将未完成/不可行条目删除。

- summary.csv：逐样本状态、目标/界/gap、耗时、费用分项、残差与输入负荷统计。
- solutions.jsonl.gz：每行一个已验解样本；values保留完整p/u/v/r/f/theta变量和值。p/r/f为MW，u/v为二元，theta沿用作者公式口径。数值未舍入，全部{len(good) * len(required):,}个变量值经压缩往返对照。
- provenance.json：输入/原件/代码身份、参数、原始运行索引、导出校验与限制。
- README.md：本说明。详细原始LP、日志和解留在runs/，不混入正式case输入目录。

原始输入数值和作者网络/备用/循环规则保持。目标沿用原费用尺度，币种/价格年份未独立确认，不擅作美元或人民币解释。达到声明gap/求解器容差不等于零gap精确最优；独立验解只证明候选在声明容差内满足所选B-θ模型及目标重算，不证明N-1、作者PTDF或AI标签复现。

输入目录provenance/issues记录输入生成时的身份与状态快照；实际求解状态看本目录summary/provenance。原I11的“未求解”部分现由本批所选B-θ运行补证，不能扩大为精确最优或其他模型已验证。保留输入快照避免改变原运行所引用的文件哈希。

Python读取一个候选：

```python
import gzip, json
with gzip.open('solutions.jsonl.gz', 'rt', encoding='utf-8') as f:
    result = json.loads(next(f))
print(result['sample_id'], result['objective_value'], result['values']['p_1_1'])
```
'''
    (output / 'README.md').write_text(readme, encoding='utf-8')
    manifest = {'case_id': CASE_ID, 'batch_id': state['batch_id'], 'created_utc': datetime.now(timezone.utc).isoformat(),
                'publication_status': 'unpublished', 'statistics': statistics, 'input_comparison': comparison,
                'parameters': state['parameters_per_sample'], 'parallel_workers': state['workers'],
                'input_and_code_identity': state['input_identity'], 'batch_script_sha256': state['batch_script_sha256'],
                'export_script_sha256': sha(Path(__file__)), 'batch_progress_sha256': sha(folder / 'progress.json'),
                'source_batch_summary_sha256': sha(folder / 'summary.csv'), 'raw_run_index': raw_hashes,
                'candidate_source_sha256': solution_hashes, 'all_exported_values_roundtrip_equal': True,
                'input_issue_snapshot_sha256': sha(CASE / 'issues.json'),
                'execution_issue_update': {'source_issue_id': 'I11',
                    'scope': 'Recorded independent samples under the author cell30 B-theta model only',
                    'attempted_samples': len(rows), 'verified_candidates': len(good),
                    'note': 'Execution evidence supplements the earlier not_run input snapshot; exact optimality, N-1, PTDF and author AI labels are not certified.'},
                'artifacts': {p.name: sha(p) for p in output.iterdir() if p.is_file()},
                'limitations': ['Solver optimal status is relative to recorded tolerances and gap.',
                                'Currency/price-year and pre-existing source issues remain disclosed.',
                                'No line N-1/PTDF/AI-label reproduction is claimed.', 'Nothing uploaded.']}
    atomic_json(output / 'provenance.json', manifest)
    # Publish only a fully checked local directory; validate both absolute
    # paths before the Windows directory rename. No original data is moved.
    allowed = (ROOT / 'results' / CASE_ID).resolve()
    if not output.resolve().is_relative_to(allowed) or not final_output.resolve().is_relative_to(allowed):
        raise ValueError('Result directory rename outside intended output area')
    output.rename(final_output)
    output = final_output
    preview = make_preview(output, statistics, rows, examples, comparison)
    atomic_json(AUX / 'export_review.json', {'pass': True, 'statistics': statistics,
                                           'input_values_unchanged': True, 'candidate_roundtrip_equal': True,
                                           'result_directory': str(output), 'preview': str(preview),
                                           'provenance_sha256': sha(output / 'provenance.json')})
    print(json.dumps({'status': 'exported_verified_results', 'statistics': statistics,
                      'result_directory': str(output), 'preview': str(preview)}, ensure_ascii=False))


def make_preview(output, stats, rows, examples, comparison):
    plot = AUX / 'batch_overview.png'
    os.environ['MPLCONFIGDIR'] = str(AUX / 'plot_cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font = Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        plt.rcParams['font.family'] = FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus'] = False
    good = [r for r in rows if r.get('objective_value') not in ('', None) and r['independent_status'] == 'feasible_within_declared_tolerances']
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), layout='constrained')
    if good:
        costs = [float(r['objective_value']) for r in good]
        axes[0].hist(costs, bins=24, color='#286b87', edgecolor='white')
        axes[0].set(xlabel='目标值（原费用单位）', ylabel='样本数', title='目标值分布')
        axes[1].scatter([r['peak_load_MW'] for r in good], costs, s=9, alpha=.4, color='#2b8b70')
        axes[1].set(xlabel='峰值总负荷（MW）', ylabel='目标值（原费用单位）', title='输入负荷与新增求解结果')
        axes[2].hist([float(r['solver_seconds']) for r in good], bins=24, color='#b88a43', edgecolor='white')
        axes[2].set(xlabel='COPT求解时间（秒）', ylabel='样本数', title='逐样本求解耗时')
    fig.suptitle(f'IEEE24：{stats["attempted_samples"]}个样本已运行，{stats["verified_candidates"]}个候选通过独立验解', fontsize=15)
    fig.savefig(plot, dpi=150)
    plt.close(fig)
    sample = examples.get('sample1')
    example_text = ''
    if sample:
        v, r = sample['values'], sample['run']
        example_text = f'''原样本1：目标{r['objective_value']:.8f}，最好界{r['best_bound']:.8f}，gap={r['relative_gap'] * 100:.6f}%。例如G1第1时段的结果为u={v['u_1_1']}, p={v['p_1_1']:.8f} MW, r={v['r_1_1']:.8f} MW；线路1同小时潮流{v['f_1_1']:.8f} MW。这些是新增决策结果，不是对原Pmax、负荷或线路参数的修改。
'''
    status_rows = '\n'.join(f'| {name} | {count} |' for name, count in stats['status_counts'].items())
    text = f'''# IEEE24全量结果与原始数据对照

本次全部在本地完成，未上传。源模型为作者Notebook第30单元B-θ UC，保持原15机组记录、38物理线路、成本、备用、循环边界和原爬坡公式。

| 项目 | 实际结果 |
|---|---:|
| 独立24小时样本已运行 | {stats['attempted_samples']} / {stats['requested_samples']} |
| 有完整候选且通过独立验解 | {stats['verified_candidates']} |
| 候选满足设置的相对gap阈值 | {stats['gap_target_met_candidates']} |
| 未获得合格候选的样本 | {len(stats['without_verified_candidate_ids'])} |
| 导出并逐值往返核对的决策变量值 | {stats['compressed_candidate_values_checked']:,} |
| 批量墙钟时间（秒，含并行及复用策略） | {stats['batch_wall_seconds']:.3f} |
| 全部样本求解器时间之和（秒，含复用首例） | {stats['sum_solver_seconds_including_reused']:.3f} |
| 候选最大MW约束违反量 | {stats['max_MW_violation']} |
| 候选最大二元距离 | {stats['max_binary_distance']} |

| 求解状态 | 样本数 |
|---|---:|
{status_rows}

达到声明gap/求解器容差与精确最优分开；独立验解重算约束和目标，不单独证明最优。币种/价格年份仍沿用未确认状态，不能改称人民币或美元。失败/未获候选的样本保留在summary，未删除。未获合格候选ID：{stats['without_verified_candidate_ids']}。

![全量结果概览]({plot.resolve().as_posix()})

## 与原始数据相比，改变了什么

| 内容 | 原作者输入 | 整理后输入 | 数值是否改变 |
|---|---|---|---|
| 机组 | 逗号分隔DAT，15条×15字段 | generators.json，字段和原编号保留 | {comparison['generator_numeric_values_compared']}个数逐项相同 |
| 线路 | 逗号分隔DAT，38条×6字段 | branches.json，并联记录分别保留 | {comparison['branch_numeric_values_compared']}个数逐项相同 |
| 负荷 | 无标题TXT，1800×576 | CSV.gz，增加sample_id和时段/节点列名 | {comparison['load_tokens_compared']:,}个数值文本逐项相同 |
| 来源/缺陷 | 分散在README、代码和已查记录中 | provenance、issues及共享字典/模型说明 | 仅新增身份、说明和状态 |
| 运行结果 | 原五文件未提供本项目求解结果 | 逐样本目标、界、gap、状态、全部变量和验解报告 | 新计算结果，不回写输入 |

五份原件及三份核心输入的身份核对通过。没有增删机组/物理线路，没有调整负荷、费用、备用或边界以制造可行。这里没有核对作者原训练标签或作者全部参考结果，不声称成本复现论文。

输入provenance/issues是数据生成时的快照，其中not_run不作为当前运行统计；当前求解和验解以results目录及总目录索引为准。原I11中“未求解”的部分由这批B-θ运行补证，其他来源/模型范围限制继续披露。

## 现在的目录结构

```text
UC_database_sta/
├─ sources/rpglab-ieee24/                 原件身份相同副本
├─ cases/rpglab_ieee24_native_v1/         六份正式输入/说明
│  ├─ generators.json
│  ├─ branches.json
│  ├─ demand_wide.csv.gz
│  ├─ issues.json
│  ├─ provenance.json
│  └─ README.md
├─ docs/profiles/rpglab-ieee24-native/     共享字段字典和模型规则
├─ results/rpglab_ieee24_native_v1/{output.name}/
│  ├─ summary.csv                        看全体样本状态和数值
│  ├─ solutions.jsonl.gz                 已验解候选的完整变量
│  ├─ provenance.json                    输入/代码/运行身份与核对结果
│  └─ README.md
├─ runs/rpglab_ieee24_native_v1/          每次运行的LP、原解、日志和验解证据
└─ scripts/                             可复跑整理、求解、验解和汇总工具
```

原作者DAT/TXT/Notebook仍在原学习目录，未覆盖。正式case中没有重复的sample_0001预览；共享说明不按样本复制。结果包只保留四份主要交付，详细运行证据另外存放。

## 结果中的一行是什么

{example_text}

summary.csv一行代表一个完整24小时样本；solutions.jsonl.gz一行代表一个已验解样本的全部2928个变量。求解gap、最大约束残差和来源未明事项分别表示不同内容，具体限制继续看issues和模型说明。

结果目录：[{output.name}]({output.resolve().as_posix()})。
'''
    preview = PROJECT / 'UC_dataset/learning/辅助材料/17_全量求解结果与原数据对照.md'
    preview.write_text(text, encoding='utf-8')
    return preview


if __name__ == '__main__':
    if hasattr(__import__('sys').stdout, 'reconfigure'):
        __import__('sys').stdout.reconfigure(encoding='utf-8')
    main()
