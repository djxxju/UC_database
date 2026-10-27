"""Build a lossless native IEEE24 data package; never run the source Notebook.

Default is offline. --fetch-source explicitly restores only the five pinned files.
"""
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "rpglab_ieee24_native_v1"
PROFILE = "rpglab-ieee24-native/1.0.0"
PROFILE_DIRECTORY = "docs/profiles/rpglab-ieee24-native"
CASE_FILES = {"generators.json", "branches.json", "demand_wide.csv.gz", "issues.json", "provenance.json", "README.md"}
COMMIT = "d9fb2a1c92c86b9d16c8fa30372b74cd3c86d89e"
BASE = f"https://raw.githubusercontent.com/rpglab/GNN-LSTM_C-V-R-SCUC/{COMMIT}/"
SUB = "Data/IEEE24Bus/DataCollectionOptimization%28BaseSCUC%29/"
FILES = {
    "GenData_1GPerBus.dat": ("9123f4b61b33b7b730844115c62d91aefa1848eaa35ccc24bf4108d3a274f063", 1364, SUB + "GenData_1GPerBus.dat"),
    "dataFileTxInfo24Bus.dat": ("43c8db81a95474a5a51feff486f8d2b142c16744d5657dace70fe0b8657c2a88", 1271, SUB + "dataFileTxInfo24Bus.dat"),
    "demand24Bus.txt": ("d027fbaf96798035bbcea50b47ccf65f0f04d2b9489067c510e60bac415f7b25", 13998278, SUB + "demand24Bus.txt"),
    "Spatio_Temporal_UC_Acceleration_Process.ipynb": ("8d4085b17d6ad647b41eeb926376690ac9adb4aab3d043013ed222909da01cb5", 496284, "Spatio_Temporal_UC_Acceleration_Process.ipynb"),
    "upstream_README.md": ("9102d2db5c4bca0a9af25e1fadc935d5e11941cc27f837baa0a235fc06bbf4f1", 4361, "README.md"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def gz(data):
    stream = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0, compresslevel=9) as out:
        out.write(data)
    return stream.getvalue()


def read_table(data):
    result = []
    for row in csv.DictReader(io.StringIO(data.decode("utf-8-sig"))):
        parsed = {}
        for key, value in row.items():
            number = float(value.strip())
            if not math.isfinite(number):
                raise ValueError(f"Non-finite source value: {key}")
            parsed[key.strip()] = int(number) if number.is_integer() else number
        result.append(parsed)
    return result


def field_dictionary():
    # Preserve author identifiers; units below describe the inspected formula, not
    # independently certified engineering metadata.
    entries = [
        ("genNo", "机组记录编号", "identifier", "GEN集合；编号从1开始"),
        ("genD_bus", "接入节点", "identifier", "节点外键；BUS=1..24"),
        ("genD_minUP", "最小连续开机时段", "period", "循环窗口；每时段按作者24 hour注释解释为1小时"),
        ("genD_minDN", "最小连续停机时段", "period", "循环窗口；不补固定初始历史"),
        ("genD_status", "原状态标记", "unknown", "所查两段基础模型未读取，不能当作初始启停条件"),
        ("genD_Pmax", "最大有功出力", "MW (model interpretation)", "p+r<=Pmax*u"),
        ("genD_Pmin", "最小有功出力", "MW (model interpretation)", "Pmin*u<=p"),
        ("genC_Startup", "启动费用系数", "source currency/start", "系数乘v；币种和价格年未确认"),
        ("genC_Cost", "线性出力费用系数", "source currency/(MW*model period)", "系数乘p；未换汇、未重拟合"),
        ("genC_NLoad", "空载费用系数", "source currency/model period", "系数乘u；未另造二次费用"),
        ("SPRamp", "备用出力上限系数", "MW (model interpretation)", "r<=SPRamp*u；响应时长待查"),
        ("NSRamp", "未使用的爬坡相关字段", "unknown", "基础模型声明但未用于约束；原值保留"),
        ("HRamp", "相邻时段出力变化系数", "MW/model period", "按作者原约束；t=1与t>1的上爬坡状态因子不同"),
        ("StartRamp", "启停过程出力变化系数", "MW/model period", "按作者原上下爬坡公式保留"),
        ("gen_Style", "类别编码", "unknown", "编码未确认，基础模型未读取"),
        ("branchNo", "线路记录编号", "identifier", "保留38条物理记录及并联线路"),
        ("branch_fbus", "线路正方向起点", "identifier", "节点外键"),
        ("branch_tbus", "线路正方向终点", "identifier", "节点外键"),
        ("branch_b", "潮流公式电纳系数", "p.u. coefficient (formula evidence)", "(theta_to-theta_from)*b=p/100；不把它当电抗；原始工程基准追溯待闭合"),
        ("branch_rateA", "基础模型正常线路限额", "MW (model interpretation)", "-rateA<=flow<=rateA"),
        ("branch_rateC", "另一档线路限额", "MW (model interpretation)", "基础模型未读取；工况定义待查"),
        ("demand24Bus.txt", "节点有功负荷", "MW (model interpretation)", "无表头；原行=sample_id，列=24*(t-1)+bus"),
    ]
    return [{"source_field": key, "chinese_name": cn, "unit_or_type": unit,
             "mapping": key if key != "demand24Bus.txt" else "demand_wide.csv.gz: sample_id,t01_bus01,...,t24_bus24",
             "model_use_or_limit": use} for key, cn, unit, use in entries]


def issues():
    return [
        {"issue_id": "I01", "fields": ["genD_status", "gen_Style", "NSRamp"], "status": "ambiguous", "description": "原值保留；类别/状态/未使用字段定义尚未确认。", "impact": "不阻塞所查循环基础模型的数据读取；阻塞跨模型语义映射。"},
        {"issue_id": "I02", "fields": ["currency", "price_year"], "status": "not_documented_in_selected_sources", "description": "费用币种与价格年份尚未确认，禁止换汇或跨币种比较。", "impact": "费用数值保留，不能声称跨来源经济可比。"},
        {"issue_id": "I03", "fields": ["SPRamp_response_duration"], "status": "ambiguous", "description": "公式上限明确，备用响应时间口径尚未确认。", "impact": "不能改作统一10分钟/15分钟备用而不生成派生版本。"},
        {"issue_id": "I04", "fields": ["branch_b_engineering_base", "branch_rateC_operating_condition"], "status": "ambiguous", "description": "p/100为原公式的显式功率标度；原始工程基准与rateC工况追溯未闭合。", "impact": "保留原公式和原系数，不作交流网络或跨库等值认证。"},
        {"issue_id": "I05", "fields": ["G7_source_mapping", "G7_zero_cost_rationale"], "status": "partially_traced", "description": "节点14零有功记录与上游同步调相机对应为有据推断；作者保留目的和逐条变换未闭合。", "impact": "不删G7、不固定u；p=r=0仍保留启停标签等价性。"},
        {"issue_id": "I06", "fields": ["G13_source_mapping", "G13_startup_no_load_cost_rationale"], "status": "partially_traced", "description": "上游六台50MW水电聚合有证据支持；当前零启动/空载费与完整变换规则未闭合。", "impact": "不补造水库/水文约束，不擅改费用。"},
        {"issue_id": "I07", "fields": ["fixed_initial_commitment", "initial_power", "initial_on_off_history"], "status": "not_applicable_to_cyclic_profile", "description": "作者以24→1循环闭合启停、最小开停和爬坡，不使用固定时域前历史。", "impact": "切换到固定初始条件模型时必须另行定义并发布派生版本。"},
        {"issue_id": "I08", "fields": ["commitment24Bus.txt", "flows24Bus.txt", "reference_dispatch_and_reserve"], "status": "not_collected", "description": "启停和潮流读取文件不在当前五份原件中；未取得可供独立验解的调度/备用记录，不表示作者未公开。未核对真实标签或样本打乱配对。", "impact": "不能复现AI标签或独立验解作者结果。"},
        {"issue_id": "I09", "fields": ["PTDF_Matrix.csv"], "status": "not_collected", "description": "Notebook cell44读取的作者PTDF矩阵未在当前五份原件中。", "impact": "作者PTDF执行路径未复现；B-theta公式可静态审查。"},
        {"issue_id": "I10", "fields": ["line_contingency_set"], "status": "not_defined_in_inspected_base_formulations", "description": "所查B-theta/PTDF两段未显式枚举线路N-1约束。", "impact": "保留来源SCUC名称；本profile仅称带网络UC及作者每机组备用规则，不认证N-1网络安全。"},
        {"issue_id": "I11", "fields": ["feasible_schedule", "optimality_certificate", "independent_solution_check"], "status": "not_run", "description": "本项目未构建/求解完整UC，未产生或独立验算候选调度。", "impact": "数据检查/必要条件通过不证明可行或最优。"},
        {"issue_id": "I12", "fields": ["sample_probability", "calendar_date", "time_zone"], "status": "not_defined_for_selected_profile", "description": "1800行作为独立24时段样本，未赋予随机场景概率或日历时区。", "impact": "不把独立样本拼成连续1800天或概率情景树。"},
        {"issue_id": "I13", "fields": ["paper_version_system_size"], "status": "ambiguous", "description": "作者arXiv预印本v1 TableI列IEEE24为17机组/3393MW，而本固定GitHub输入是15条机组记录/3405MW；差异原因待查，不推广到最终期刊版。", "impact": "不能仅凭系统名称或总成本将当前版本认作论文表格完全复现。"},
    ]


def annotate_issues(entries):
    notebook_url = f"https://github.com/rpglab/GNN-LSTM_C-V-R-SCUC/blob/{COMMIT}/Spatio_Temporal_UC_Acceleration_Process.ipynb"
    gen_url = BASE + SUB + "GenData_1GPerBus.dat"
    evidence = {
        "I01": (["Notebook cells 30/45: source field reads and Param declarations; GenData header"], [notebook_url, gen_url], ["cross_model_field_mapping"]),
        "I02": (["Selected original README and GenData cost column headers do not settle ISO currency/price year"], [BASE + "README.md", gen_url], ["cross_source_economic_comparison"]),
        "I03": (["Notebook cells 30/45 reserve_rr1_f: r<=SPRamp*u"], [notebook_url], ["reserve_response_profile_conversion"]),
        "I04": (["Notebook cell30 pf_theta_f: (theta_to-theta_from)*b=p/100; branch_rateC not read in cells30/45"], [notebook_url, BASE + SUB + "dataFileTxInfo24Bus.dat"], ["engineering_unit_certification", "AC_network_adaptation"]),
        "I05": (["GenData record genNo=7, bus=14, Pmax=Pmin=0", "UW RTS96 Table7 node114 Sync Cond; mapping to this transformed RPG record remains an inference", "MATPOWER6.0 case24_ieee_rts source line0079 has node14 SynCond, Pmin=Pmax=0"], [gen_url, "https://labs.ece.uw.edu/pstca/rts/rts96/Table-07.txt", "https://matpower.org/docs/ref/matpower6.0/case24_ieee_rts.html"], ["source_transformation_reproduction", "AI_label_interpretation"]),
        "I06": (["GenData record genNo=13, bus=22, Pmax=300, cost coefficients all zero", "Notebook cell2 says multiple units at one bus were combined; RTS96 Table6/7 six50MW hydro records support aggregation, not complete transformation equivalence", "Author2022 dissertation printedp27 Table2.1 supports an older six50MW zero-output-cost group, not current startup/no-load costs"], [gen_url, notebook_url, "https://labs.ece.uw.edu/pstca/rts/rts96/Table-06.txt", "https://labs.ece.uw.edu/pstca/rts/rts96/Table-07.txt", "https://rpglab.github.io/pdfs/team/2022-12-01_Arun_Dissertation.pdf#page=51"], ["source_transformation_reproduction", "hydro_model_extension"]),
        "I07": (["Notebook cells30/45 var_v_f/Min_up_f/Min_dn_f/gen_HrRampUp_f/gen_HrRampDn_f wrap time 24 to1; commented initial-status block"], [notebook_url], ["conversion_to_fixed_initial_history_profile"]),
        "I08": (["Notebook data-reading cells reference commitment24Bus.txt and flows24Bus.txt; current five-file scope excludes them", "No author candidate schedule has been independently checked"], [notebook_url], ["ML_label_pairing", "independent_solution_check"]),
        "I09": (["Notebook cell44 reads PTDF_Matrix.csv"], [notebook_url], ["author_PTDF_execution_reproduction"]),
        "I10": (["Inspected formulation definitions in cells30/45 use normal rateA and per-generator reserve; no explicit line-contingency index/set there"], [notebook_url], ["N_minus_1_network_security_claim"]),
        "I11": (["Project execution state as of2026-10-26: no solver or fullUC model executed"], [], ["feasibility_claim", "optimality_claim", "benchmark_solution_publication"]),
        "I12": (["demand24Bus.txt has1800 independent rows; source reading gives row/sample order, no row-level probability/date/timezone mapping selected"], [BASE + SUB + "demand24Bus.txt", notebook_url], ["stochastic_probability_model", "calendar_time_series_reconstruction"]),
        "I13": (["arXiv2306.01570v1 TableI, PDFp7: IEEE24 listed17 generators/3393MW", "Current pinned GenData:15 records, sum Pmax3405MW; final journal version was not inferred from preprint"], ["https://arxiv.org/pdf/2306.01570v1#page=7", gen_url], ["paper_version_equivalence_claim"]),
    }
    for entry in entries:
        locations, urls, blocking = evidence[entry["issue_id"]]
        entry["evidence_locations"] = locations
        entry["evidence_urls"] = urls
        entry["blocking_for"] = blocking
        entry["blocks_native_input_reorganization"] = False
    return entries


def model_profile():
    return {
        "profile": PROFILE, "source_cells_zero_based": {"btheta": 30, "ptdf": 45},
        "classification": "lossless_input_reorganization_with_explicit_native_semantics",
        "model_family": "network_UC_with_author_per_generator_reserve_rule",
        "source_name_contains_SCUC": True, "network_N_minus_1_certified": False,
        "time": {"periods": 24, "time_step_hours": 1, "evidence": "Notebook #24 hour time set; nPrd=24", "boundary": "cyclic_24_to_1"},
        "objective": "sum(g,t)[genC_Cost[g]*p[g,t]+genC_NLoad[g]*u[g,t]+genC_Startup[g]*v[g,t]]",
        "capacity": "Pmin*u<=p; p+r<=Pmax*u; 0<=r<=SPRamp*u",
        "reserve": "for every g,t: sum_h r[h,t]>=p[g,t]+r[g,t]",
        "startup": {"direct_constraint": "v_t>=u_t-u_prev", "full_constraint_implication": "minUP>=1 gives v_t<=u_t; preceding minDN>=1 gives v_t<=1-u_prev; jointly v_t is exact 0->1 indicator", "no_arbitrary_v_claim": True},
        "ramp_up": {"t1": "p1-p24<=HRamp*u24+StartRamp*v1", "t_gt_1": "pt-p_prev<=HRamp*u_t+StartRamp*v_t", "note": "原文状态因子差异保留，未改为常见公式。"},
        "ramp_down": "p_prev-p_t<=HRamp*u_t+StartRamp*(v_t-u_t+u_prev); prev(1)=24",
        "minimum_up_down": "作者循环启动窗口；保留原公式，不补初始历史。",
        "dc_flow": "(theta_to-theta_from)*branch_b=flow/100; theta_bus1=0; -rateA<=flow<=rateA",
        "nodal_balance": "local_generation+incoming_flow-outgoing_flow=load",
        "preserved_unused_fields": ["genD_status", "gen_Style", "NSRamp", "branch_rateC"],
        "physical_lines": 38, "parallel_pairs_preserved": True,
        "ML_graph_limit": "作者cell7按max合并并联为34条ML边；该图不作为物理线路等值。",
        "execution": "source Notebook was parsed only, never executed; solver/model import not tested",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="Read-only directory of the five original files")
    parser.add_argument("--output-root", type=Path, default=ROOT, help="Repository-shaped output directory")
    parser.add_argument("--fetch-source", action="store_true", help="Explicitly allow network restoration of missing pinned originals")
    args = parser.parse_args()
    outroot = args.output_root.resolve()
    source_archive = outroot / "sources/rpglab-ieee24"
    case = outroot / "cases" / CASE_ID
    profile_directory = outroot / PROFILE_DIRECTORY
    source_archive.mkdir(parents=True, exist_ok=True)
    case.mkdir(parents=True, exist_ok=True)
    unexpected = {p.name for p in case.iterdir()} - CASE_FILES
    if unexpected:
        raise ValueError(f"Case directory contains non-delivery files; archive them before rebuilding: {sorted(unexpected)}")
    fallback = ROOT.parent / "UC_dataset/learning/ieee24_rpglab"
    data = {}
    restorations = []
    for name, (digest, size, relative) in FILES.items():
        archive_name = name + ".gz" if name == "demand24Bus.txt" else name
        archived = source_archive / archive_name
        candidates = [args.source_dir / name] if args.source_dir else [archived, ROOT / "sources/rpglab-ieee24" / archive_name, fallback / name]
        payload = None
        for path in candidates:
            if path.exists():
                payload = gzip.decompress(path.read_bytes()) if path.name.endswith(".gz") else path.read_bytes()
                break
        if payload is None:
            if not args.fetch_source:
                raise FileNotFoundError(f"Missing {name}; provide --source-dir or explicitly use --fetch-source")
            request = urllib.request.Request(BASE + relative, headers={"User-Agent": "UC-native-data-restoration/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
            restorations.append({"original_name": name, "url": BASE + relative, "restored_at_UTC": datetime.now(timezone.utc).isoformat(), "method": "explicit_fetch_source"})
        if len(payload) != size or sha(payload) != digest:
            raise ValueError(f"Pinned original identity mismatch: {name}")
        data[name] = payload
        encoded = gz(payload) if name == "demand24Bus.txt" else payload
        if archived.exists() and archived.read_bytes() != encoded:
            raise ValueError(f"Refuse to overwrite a differing source archive: {archived}")
        if not archived.exists():
            archived.write_bytes(encoded)
    generators = read_table(data["GenData_1GPerBus.dat"])
    branches = read_table(data["dataFileTxInfo24Bus.dat"])
    dump(case / "generators.json", generators)
    dump(case / "branches.json", branches)
    # Profile documentation is shared, rather than repeated in every case.
    dump(profile_directory / "field_dictionary.json", field_dictionary())
    dump(profile_directory / "model_profile.json", model_profile())
    dump(case / "issues.json", {"policy": "No unknown value was filled with zero. not_collected does not imply missing upstream.", "issues": annotate_issues(issues())})
    rawrows = list(csv.reader(io.StringIO(data["demand24Bus.txt"].decode("utf-8-sig"))))
    if len(rawrows) != 1800 or any(len(row) != 576 for row in rawrows):
        raise ValueError("Unexpected source demand dimensions")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["sample_id"] + [f"t{t:02d}_bus{b:02d}" for t in range(1, 25) for b in range(1, 25)])
    for index, row in enumerate(rawrows, start=1):
        values = [value.strip() for value in row]
        if any(not math.isfinite(float(value)) or float(value) < 0 for value in values):
            raise ValueError(f"Invalid demand value in original row {index}")
        writer.writerow([index] + values)
    (case / "demand_wide.csv.gz").write_bytes(gz(buffer.getvalue().encode("utf-8")))
    readme = """# RPG Lab IEEE24：本地数据整理校验包

本包保留作者15条机组、38条线路和1800个独立24时段负荷样本；未修改原数值、成本、负荷或模型假设。profile为 `rpglab-ieee24-native/1.0.0`，与仓库既有SJTU无网络目标格式分别验收。当前为本地待共同验收，尚未发布；完整UC求解和独立验解未执行。

- `generators.json` / `branches.json`：保留原作者全部字段和编号。
- `demand_wide.csv.gz`：1800行；首列sample_id为原TXT从1计数行号；其后t01_bus01到t24_bus24。数值文本仅去除周围空白，未舍入或打乱。
- 共享字段和模型规则见 `../../docs/profiles/rpglab-ieee24-native/field_dictionary.json` 与 `../../docs/profiles/rpglab-ieee24-native/model_profile.json`；前者说明字段/单位，后者说明原成本、备用、循环边界及潮流公式。
- `issues.json`：缺失、未收集、歧义、不适用及未运行状态分别记录；G7/G13保留原值。
- `provenance.json`：固定提交、来源许可、SHA-256及转换脚本身份；原件副本见 `../../sources/rpglab-ieee24/`。

正式case仅保留上述三份数据、问题清单、来源记录和本README，共六份文件。全体样本已包含在demand中，不重复保存单样本查看文件。gzip是标准无损压缩，Python可直接读取；压缩不改变数值。缺陷先记录影响，只有影响建模或结果解释时再追查。

在仓库根目录：`python scripts/build_ieee24.py` 离线重建，`python scripts/validate_ieee24.py` 复核映射、结构、参数及全量必要条件。仅在缺原件且明确允许联网时使用 `python scripts/build_ieee24.py --fetch-source`，按固定URL恢复并校核五份原件。默认不联网、不运行Notebook或求解器。校验器需要numpy。

数据整理检查通过不能证明完整UC可行、最优或N-1网络安全；具体报告见 `../../reports/ieee24_validation.json`。作者结果标签与PTDF矩阵尚未纳入本包，不宣称已经复现其执行路径。

来源：Arun Venkatesh Ramesh and Xingpeng Li, Spatio-Temporal Deep Learning-Assisted Reduced Security-Constrained Unit Commitment, DOI 10.1109/TPWRS.2023.3313430。作者仓库 https://github.com/rpglab/GNN-LSTM_C-V-R-SCUC ，固定提交d9fb2a1c92c86b9d16c8fa30372b74cd3c86d89e；原README声明CC BY 4.0，https://creativecommons.org/licenses/by/4.0/ 。本包的重排、中文说明和校验为本项目新增材料，原作者不为这些改动背书。
"""
    (case / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    original_files = []
    for name, (digest, size, relative) in FILES.items():
        archive_name = name + ".gz" if name == "demand24Bus.txt" else name
        archived = source_archive / archive_name
        original_files.append({"original_name": name, "url": BASE + relative, "original_sha256": digest, "original_bytes": size, "first_download_date": "2026-10-24", "archive_path": archived.relative_to(outroot).as_posix(), "archive_sha256": sha(archived.read_bytes()), "encoding": "gzip of exact original bytes" if name == "demand24Bus.txt" else "exact original bytes"})
    manifest = {"source": "https://github.com/rpglab/GNN-LSTM_C-V-R-SCUC", "commit": COMMIT, "license": "CC BY 4.0 (upstream README)", "license_url": "https://creativecommons.org/licenses/by/4.0/", "citation": "Arun Venkatesh Ramesh and Xingpeng Li, Spatio-Temporal Deep Learning-Assisted Reduced Security-Constrained Unit Commitment, DOI 10.1109/TPWRS.2023.3313430", "files": original_files}
    dump(source_archive / "manifest.json", manifest)
    if restorations:
        dump(outroot / "reports/ieee24_restore_receipt.json", {"original_acquisition_date": "2026-10-24", "events": restorations, "all_pinned_hashes_verified": True})
    artifacts = {p.relative_to(outroot).as_posix(): sha(p.read_bytes()) for p in sorted(case.iterdir()) if p.is_file() and p.name != "provenance.json"}
    profile_files = {name: f"{PROFILE_DIRECTORY}/{name}.json" for name in ("field_dictionary", "model_profile")}
    profile_artifacts = {relative: sha((outroot / relative).read_bytes()) for relative in profile_files.values()}
    scripts = {"scripts/" + name: sha((ROOT / "scripts" / name).read_bytes()) for name in ("build_ieee24.py", "validate_ieee24.py")}
    dump(case / "provenance.json", {"case_id": CASE_ID, "profile": PROFILE, "schema_version": "1.1.0", "package_layout": "lean-case/1.0.0", "built_on": "2026-10-26", "classification": "lossless_input_reorganization", "status": "local_pending_joint_review", "publication_status": "unpublished", "solve_status": "not_run", "independent_solution_check": "not_run", "source": manifest, "shape": {"generators": 15, "buses": 24, "branches": 38, "samples": 1800, "periods_per_sample": 24, "nodal_load_values": 1036800}, "load_order": "sample_id=original row, 1-based; columns after sample_id ordered period then bus; 1-based", "changes": ["原件内容不变；demand原件仅作可逆gzip压缩。", "机组/线路转为保留全部原字段的JSON；负荷去除周围空白、增加显式sample_id及列名，无舍入。", "字段/模型说明放共享profile目录；问题标注保留，不补造参数或修改原模型。", "单样本查看表不作为正式交付，全部样本仍完整保存在负荷文件中。"], "script_sha256": scripts, "artifact_sha256": artifacts, "profile_files": profile_files, "profile_artifact_sha256": profile_artifacts})
    print(json.dumps({"case_id": CASE_ID, "output_root": str(outroot), "samples": 1800, "nodal_values": 1036800, "source_files_verified": 5, "status": "built_local_pending_validation"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
