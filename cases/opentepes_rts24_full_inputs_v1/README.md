# openTEPES RTS24 全时域输入审计 v1

固定版 openTEPES `5c0187063874cca4bc7af8ff97b19c6c316dd7a5` 的 RTS24 原输入有 24 个节点、38 条支路、33 条机组记录、一个 period、一个场景和一个阶段。17 张时序表覆盖全部 8,736 个原始小时。按固定版时间转换规则复算得到 4,368 个两小时有效时段。静态总容量检查通过，模型构建、COPT 适配、求解和独立验解均为 `not_run`。[审计报告](../../reports/opentepes_rts24_full_inputs_v1/README.md) · [机器报告](../../reports/opentepes_rts24_full_inputs_v1/data_validation.json) · [待核事项](issues.json)

## 基础信息（2026-11-21更新）

| 项目 | 内容 |
| --- | --- |
| 来源 | Universidad Pontificia Comillas / IIT 的 openTEPES 官方仓库 RTS24 案例 |
| 固定版本 | 5c0187063874cca4bc7af8ff97b19c6c316dd7a5 |
| 节点与分区 | 24节点、7个Zone、2个Area、1个Region |
| 机组记录 | 33条，含15 Diesel、9 Coal、2 Gas、6 Hydro、1 SynchronousCondenser；分类按原Technology字段 |
| 有功设备 | 32条正有功容量记录；调相机SC_SC001有功容量为0，无功范围−50至200 |
| 发电容量 | 原名牌合计3,405 MW；按固定版EFOR规则折减后为3,196.37 MW |
| 负荷 | 原小时峰值2,850 MW；全时域电量15,297,074.71374 MWh |
| 时间范围 | 2030年1月1日00:00至12月30日23:00（UTC+01），8,736个小时 |
| 源时间转换 | TimeStep=2，形成4,368个两小时时段，覆盖全部原始时间 |
| 是否有潮流 | 有网络潮流参数及固定源码的DC B-θ规则；实际执行状态见下文 |
| 线路 | 38条物理支路，原LineType均为AC；AC线路类型与是否采用AC潮流分别登记 |
| 参考节点 | N_113，SBase=100 |
| 拓扑 | 24节点连通、无自环，34组无向端点对，4对并联线路 |
| 完备度 | 含网络和库存数据；爬坡、最小开停与冷热启动的适用缺口见下表，未作统一A级认定 |

原始机组、线路、节点位置和全部时序输入可从[原件清单](provenance.json)中的固定地址恢复。主要文件为oT_Data_Generation_RTS24.csv、oT_Data_Network_RTS24.csv、oT_Data_NodeLocation_RTS24.csv和oT_Data_Demand_RTS24.csv。

## 拓扑与线路参数

四对并联线路分别连接 N_115—N_121、N_118—N_121、N_119—N_120、N_120—N_123，每对有两条独立Circuit记录。38条支路全部保留。按节点编号偏移100比较，连接关系及并联数与本库RPG IEEE24版本一致，电气参数、资源和模型规则另行核对。

线路包含端点、Circuit、电阻、电抗、Tap、容量和角度字段。电抗均为正，正向TTC为175—500 MW，SecurityFactor均1。反向TTCBck全部为空，固定版读取器回退到正向容量。3条Voltage为空。角度原值±1.047197551，文档单位为度，不能据数值直接解释为±60度。当前资料支持基础网络潮流口径，N−1事故分析仍需专门的事故集和规则证据。

## 机组与约束要素

| 要素 | 本例原始数据与规则 |
| --- | --- |
| 功率上下限 | MaximumPower 33条有值；MinimumPower 27条有值、6条空，空值默认及动态限额回退按固定源码解释 |
| 常规爬坡 | RampUp、RampDown均33条空，固定版零速率条件跳过相应爬坡限制 |
| 最小开停时间 | UpTime、DownTime、StableTime均33条空，不能据选项打开便称参数齐备 |
| 备用 | 两区上下备用在全部8,736小时均显式为0 |
| 启动费用 | StartUpCost 24条有标量值、9条空；当前输入无热/冷分档费用及切换时长规则 |
| 停机及空载项 | ShutDownCost、ConstantTerm均为空，读取器默认值与原表显式零区分 |
| 生产费用 | 原燃料、线性、运维及排放系数配合固定源码计算，费用单位按source profile |
| 储能/水电 | 6条原Hydro记录按固定源码进入库存模型；库存最小/初始/最大为0.001/0.25/0.5 GWh，效率0.7 |
| 充电与流入 | 充电功率栏全空，不能凭Pum名称假定可抽水；6列流入完整覆盖时域，外流表为空 |
| 初末边界 | 软件按源规则构造初始机组状态和出力，适用既有储能阶段末库存固定回初始值 |

Gas_C31、Gas_C32、Gas_C33原Technology为Coal，水电、制氢、产热转换系数同时为正。按完整固定源码条件，三条均在h/es之外；作者填写这些系数的意图仍待核。[待核事项](issues.json) · [完整输入审计](../../reports/opentepes_rts24_full_inputs_v1/README.md)

## 恢复原件

正式包通过来源引用使用原始 CSV。任选以下途径恢复 44 份文件，保留文件名与原字节，并取得固定版仓库根 `LICENSE`。

1. 从固定版 RTS24 目录取得原表。逐文件下载地址、原始 SHA256、Git blob SHA1 与字节数列于 `provenance.json`。[固定版 RTS24](https://github.com/IIT-EnergySystemModels/openTEPES/tree/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/cases/RTS24) · [原件清单](provenance.json)
2. 从原始库第 08 批 Release 下载 `Comillas-openTEPES-5c018706.zip`。按 `provenance.json` 核对 ZIP SHA256，解压后使用其中仓库根的 `openTEPES/cases/RTS24` 与 `LICENSE`。本次重新确认了附件元数据，逐文件审计对本地固定版原件执行。[原始库整包](https://github.com/djxxju/UC_datas_codex/releases/download/official-data-2026-10-18-batch08/Comillas-openTEPES-5c018706.zip)

## 审计复跑

从正式库根目录用 Python 3.10 或更新版本运行，依赖为 Python 标准库。把命令中的路径换成恢复的原始文件路径。`--output` 需要新的文件名，也可省略并输出到标准输出。

```text
python -B scripts/opentepes_rts24/audit_rts24.py --source-dir path/to/RTS24 --license-file path/to/LICENSE --output rts24_audit_rerun.json
python -B scripts/opentepes_rts24/test_audit_rts24.py --source-dir path/to/RTS24 --license-file path/to/LICENSE
```

[时间和模型规则](../../docs/profiles/opentepes-rts24-source-input-audit/1.0.0/README.md) · [逐例校验和](../../reports/opentepes_rts24_full_inputs_v1/checksums.sha256)

## 来源与许可

openTEPES 由 Universidad Pontificia Comillas 的 Instituto de Investigación Tecnológica（IIT）开发。上游项目建议引用 Andrés Ramos、Erik Quispe、Sara Lumbreras 在 *SoftwareX* 18（2022）发表的 openTEPES 软件论文。[论文 DOI](https://doi.org/10.1016/j.softx.2022.101070) · [固定版引用说明](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/README.md)

固定版仓库根附 GNU Affero General Public License version 3 文本，RTS24 目录清单中无单独许可文件。此处保留原仓库许可文本和来源引用，原始 CSV 由上述入口恢复。[固定版根许可](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/LICENSE) · [许可原文副本](LICENSE.txt)
