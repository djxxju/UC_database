"""只读校验邓俊2015六规模输入草稿；来源冲突与结构检查分别报告。"""
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCALES = (10, 20, 40, 60, 80, 100)
PROFILE = 'deng2015-4bin-ramp-inputs/1.0.0'
SCHEMA = 'schema/deng2015-4bin-ramp-inputs-1.0.0.schema.json'

def need(condition, message):
    if not condition:
        raise ValueError(message)

def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, '重复JSON键：' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('非有限JSON数值：' + value)
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=invalid)

def check_case(data, base):
    n = data['generator_count']
    need(n in SCALES and len(data['generators']) == n, '机组数量错误')
    need(data['horizon_hours'] == 24 and data['time_step_hours'] == 1, '时域错误')
    units = {'initial_p': 'MW', 'ramp_up': 'MW/h', 'ramp_down': 'MW/h', 'pstart': 'MW', 'pshut': 'MW'}
    need(all(data['field_units'].get(k) == v for k, v in units.items()), '新增字段单位错误')
    compared = 0
    for i, g in enumerate(data['generators']):
        b = base['generators'][i % 10]
        need(g['id'] == i + 1 and g['source_unit_id'] == i % 10 + 1 and g['copy_index'] == i // 10 + 1, '复制编号错误')
        for key, value in g.items():
            need(type(value) in (int, float) and math.isfinite(value), '机组数值非法：' + key)
        need(0 <= g['pmin_mw'] <= g['pmax_mw'], '出力上下限错误')
        need(g['initial_status_hours'] != 0, '初始状态未确定')
        if g['initial_status_hours'] < 0:
            need(g['initial_p'] == 0, '停机初始出力应为0')
        else:
            need(g['pmin_mw'] <= g['initial_p'] <= g['pmax_mw'], '在线初始出力越界')
        need(g['ramp_up'] >= 0 and g['ramp_down'] >= 0, '爬坡上限为负')
        need(all(g['pmin_mw'] <= g[k] <= g['pmax_mw'] for k in ('pstart', 'pshut')), '启停功率上限越界')
        for key in b:
            if key not in ('id', 'source_unit_id', 'copy_index'):
                need(g[key] == b[key], f'复制参数变化：机组{i+1}/{key}')
                compared += 1
    ts = data['time_series']
    need(ts['hour'] == list(range(1, 25)), '时段编号错误')
    for key in ('demand_mw', 'reserve_mw'):
        need(len(ts[key]) == 24, '时序长度错误')
        for value, original in zip(ts[key], base['time_series'][key]):
            need(type(value) in (int, float) and math.isfinite(value) and value >= 0, '时序数值非法')
            if key == 'reserve_mw':
                continue
            need(Decimal(str(value)) == Decimal(str(original)) * (n // 10), '负荷倍数错误')
    need(all(Decimal(str(r)) == Decimal(str(d)) * Decimal('0.1') for d, r in zip(ts['demand_mw'], ts['reserve_mw'])), '备用比例错误')
    cap = sum(g['pmax_mw'] for g in data['generators'])
    margins = [float(Decimal(str(cap)) - Decimal(str(d)) - Decimal(str(r))) for d, r in zip(ts['demand_mw'], ts['reserve_mw'])]
    need(min(margins) >= 0, '容量必要条件不通过')
    return {'parameter_comparisons': compared, 'total_pmax_mw': cap, 'min_margin_mw': min(margins), 'per_period_margin_mw': margins}

def main():
    schema = read(ROOT / SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    base = read(ROOT / 'cases/deng2015_uc10_ramp_inputs_v1/input.json')
    for n in SCALES:
        case = f'deng2015_uc{n}_ramp_inputs_v1'
        folder = ROOT / 'cases' / case
        data = read(folder / 'input.json')
        validator.validate(data)
        need(data['case_id'] == case, '算例身份错误')
        result = check_case(data, base)
        report = read(ROOT / 'reports' / case / 'data_validation.json')
        need(report['deterministic_checks'] == result, '检查报告与实际输入不一致')
        need(report['solve_status'] == report['independent_solution_check'] == 'not_run', '执行状态错误')
        need(report['input_sha256'] == hashlib.sha256((folder / 'input.json').read_bytes()).hexdigest(), '输入哈希错误')
        source = read(folder / 'provenance.json')
        need(source['source_verification'] == report['source_verification'], '来源状态不一致')
        need(source['source_verification']['status'] == 'VERIFIED', '限定源字段核查未通过')
        need(report['publication_readiness'] == 'ready_for_upload_with_disclosed_license_status', '发布边界错误')
        for line in (ROOT / 'reports' / case / 'checksums.sha256').read_text(encoding='utf-8').splitlines():
            digest, name = line.split('  ', 1)
            target = (ROOT / name).resolve()
            need(target.is_relative_to(ROOT.resolve()), '清单路径越界')
            need(hashlib.sha256(target.read_bytes()).hexdigest() == digest, '文件哈希不符：' + name)
        print(f'{n}台：Schema/参数/复制/备用/容量必要界/哈希通过；限定源字段已核，未求解')

if __name__ == '__main__':
    main()
