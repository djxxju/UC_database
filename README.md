# UC 标准化算例库

## 仓库结构与后续增加算例

```text
UC_database/
├─ cases/<case_id>/             每个算例的正式输入、来源、缺口和说明
├─ reports/<case_id>/           数据检查及逐算例哈希清单
├─ results/<case_id>/           有真实求解时的参考总表与验解摘要
├─ docs/profiles/<profile>/     共享字段、单位和模型规则
├─ schema/                     各profile格式规范
├─ scripts/                    按profile支持的共享程序
├─ templates/case/             新算例说明模板
├─ catalog.json                全库索引，每例独立profile/类别/状态
└─ README.md                   人工浏览入口
```

[新增算例入库规则](docs/contributing.md) · [说明模板](templates/case/README.md)

| 算例编号 | 模型与规模 | 当前结果 |
|---|---|---|
| [rpglab_ieee24_native_v1](cases/rpglab_ieee24_native_v1/README.md) | 原B-θ网络UC，15机组记录/24节点/38物理线路，1800个24小时样本 | 数据检查通过，全部样本求解与独立验解通过 |

每新增一个算例，在cases/reports中使用同一个case_id；有实际求解结果时再增加对应results目录，并更新catalog及本表。模型类别用于索引筛选，具体输入与约束由每例profile定义。模板不会作为正式算例计数。

## RPG Lab IEEE24 原模型算例 v1

[输入与使用说明](cases/rpglab_ieee24_native_v1/README.md) · [目录索引](catalog.json) · [参考结果](results/rpglab_ieee24_native_v1/reference_results.csv) · [校验摘要](results/rpglab_ieee24_native_v1/verification.json)

24节点、15条机组记录、38条物理线路、1800个独立24小时样本。三份核心输入数值与固定来源一致；保留作者B-θ模型、备用、爬坡和循环边界。65项数据检查通过，1800样本均达到所设相对gap0.01%并通过独立候选验算。不是N-1、作者PTDF或AI标签复现。缺口见issues；费用币种/价格年尚未确认。

本次仅提供标准化数据、必要规则/来源/缺口、校验摘要、参考结果总表及共享工具。原件缓存、逐次LP/日志、完整变量与工作材料不随本次发布重复上传。

命名规则：case_id采用`来源_系统_模型或变体_v主版本`，本例为`rpglab_ieee24_native_v1`。每例放cases/<case_id>/，参考结果放results/<case_id>/；共享工具和规则全库各一份。样本ID与源TXT行号一致。正式文件名固定，不拼接临时日期或批次号；运行时间和批次留在来源/验解记录。

### 读取与复算

读取JSON/CSV.gz只需Python标准库。需要恢复原件、重新数据校验或建模时，在仓库目录执行（恢复需联网，求解需另行安装有效COPT）：

```text
python -m pip install -r requirements-ieee24.txt
python scripts/build_ieee24.py --fetch-source --output-root reproduce_ieee24
python scripts/validate_ieee24.py --root reproduce_ieee24
python scripts/solve_ieee24.py --case-dir reproduce_ieee24/cases/rpglab_ieee24_native_v1 --sample-id 1 --time-limit 300 --relative-gap 0.0001 --threads 1
```

恢复工具按记录的固定版本URL和哈希取得五份源文件。重建写到独立reproduce_ieee24目录，不覆盖本次正式输入/结果；重新运行产生新记录，不改写已公布的参考结论。第三条命令只做数据检查，第四条才启动求解。

本例原数据许可为CC BY 4.0（上游README），论文引用与原件SHA-256在provenance中。按原许可署名，来源未明处继续披露；不授予原作者未授予的权利。
