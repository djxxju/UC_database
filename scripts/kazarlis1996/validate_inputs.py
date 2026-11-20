"""只读核对Kazarlis六规模输入、Schema、复制关系及哈希；不求解。"""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
def read(p):
    return json.loads(p.read_text(encoding="utf-8"))
def need(condition, message):
    if not condition:
        raise ValueError(message)
def main():
    schema = read(ROOT / "schema/kazarlis1996-table-inputs-0.1.0.schema.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    base = read(ROOT / "cases/kazarlis1996_uc10_inputs_v1/input.json")
    total = 0
    for n in [10, 20, 40, 60, 80, 100]:
        case = f"kazarlis1996_uc{n}_inputs_v1"
        folder = ROOT / "cases" / case
        data = read(folder / "input.json")
        validator.validate(data)
        need(data["case_id"] == case and data["generator_count"] == len(data["generators"]) == n, "规模或身份错误")
        need(data["time_series"]["hour"] == list(range(1, 25)), "时域错误")
        for i, g in enumerate(data["generators"]):
            original = base["generators"][i % 10]
            need(g["id"] == i + 1 and g["source_unit_id"] == i % 10 + 1 and g["copy_index"] == i // 10 + 1, "复制编号错误")
            for key in original:
                if key not in ["id", "source_unit_id", "copy_index"]:
                    need(g[key] == original[key], f"机组参数变化：{case}/{key}")
                    total += 1
        for key in ["demand_mw", "reserve_mw"]:
            for a, b in zip(data["time_series"][key], base["time_series"][key]):
                need(Decimal(str(a)) == Decimal(str(b)) * (n // 10), "时序倍数错误")
        need(all(Decimal(str(r)) == Decimal(str(d)) * Decimal("0.1") for d, r in zip(data["time_series"]["demand_mw"], data["time_series"]["reserve_mw"])), "备用规则错误")
        for name in data["documentation"].values():
            need((folder / name).is_file(), "来源或缺口引用不存在")
        provenance = read(folder / "provenance.json")
        need(provenance["solve_status"] == provenance["independent_solution_check"] == "not_run", "未执行状态错误")
        report = read(ROOT / "reports" / case / "data_validation.json")
        cap = sum(g["pmax_mw"] for g in data["generators"])
        margin = [cap - d - r for d, r in zip(data["time_series"]["demand_mw"], data["time_series"]["reserve_mw"])]
        need(report["all_unit_capacity_necessary_condition"]["per_period_margin_mw"] == margin, "容量报告错误")
        need(report["input_sha256"] == hashlib.sha256((folder / "input.json").read_bytes()).hexdigest(), "输入哈希错误")
        for line in (ROOT / "reports" / case / "checksums.sha256").read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            target = (ROOT / name).resolve()
            need(target.is_relative_to(ROOT), "清单路径越界")
            need(hashlib.sha256(target.read_bytes()).hexdigest() == digest, f"哈希错误：{name}")
        print(f"{n}台：格式、复制、备用、容量报告和哈希通过；未求解")
    print(f"六规模通过，逐机组参数比较{total}项；不表示UC可行或许可确认。")
if __name__ == "__main__":
    main()
