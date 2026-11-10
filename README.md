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

## 算例索引

当前共 6 个算例，涵盖 1 个可识别的 24 节点基础电网和 1 个 OR-LIB 单节点基准系列。IEEE24 原版、旧 33 记录版和 RTS24 分别保留自己的数据版本与模型状态。

| 算例 | 分类与规模 | 校验与结果 | 输入入口 |
|---|---|---|---|
| RPG Lab IEEE24 原版 | 网络 UC，24 节点，15 条机组记录，1,800 个 24 小时样本 | 全部样本完成求解与独立验解 | [算例目录](cases/rpglab_ieee24_native_v1/) |
| RPG Lab IEEE24 旧 33 记录版 | 网络 UC 输入版，24 节点，1,500 行负荷 | 已整理及逐值核对，旧时段映射待核，未求解 | [算例目录](cases/rpglab_ieee24_legacy33_inputs_v1/) |
| OR-LIB 10 台 | 单节点 UC，24 小时 | Gurobi 与 COPT 结果通过独立验解，含 0.243366 MWh 削负荷 | [算例目录](cases/ucjl_orlib_10_0_1_w_native_v1/) · [JSON](cases/ucjl_orlib_10_0_1_w_native_v1/input.json) |
| OR-LIB 20 台 | 单节点 UC，24 小时 | COPT 限时获得候选解，独立验解通过 | [算例目录](cases/orlib_20_0_1_w/) · [JSON](cases/orlib_20_0_1_w/input.json) |
| OR-LIB 50 台 | 单节点 UC，24 小时 | COPT 达到 0.01% 相对 gap 门槛，独立验解通过 | [算例目录](cases/orlib_50_0_1_w/) · [JSON](cases/orlib_50_0_1_w/input.json) |
| openTEPES RTS24 | 网络 UC，24 节点，8,736 原始小时 | 已做全时域输入校验，模型、求解与验解待执行 | [来源与恢复说明](cases/opentepes_rts24_full_inputs_v1/) |

[机器可读索引](catalog.json)为每例登记分类、版本、规模和执行状态。已发布的算例 ID 与文件路径继续保留，OR-LIB 20、50 台的发行版本见索引中的 `distribution_version`。

## 下载原始输入或按需生成 MATLAB 文件

OR-LIB 各行的 **JSON** 链接打开正式输入，可在 GitHub 文件页下载。需要 MATLAB 文件时，运行 [转换工具](docs/matlab-export.md)，选中已下载的 JSON，再选择另存位置。工具从同一份输入生成本地 `.mat`，仓库只维护正式输入。当前转换入口支持上表三份 OR-LIB 单节点 24 小时 JSON。

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
