# Kazarlis 1996 60 台 24 小时 UC 输入 v1

本例提供 60 台火电机组参数、24 小时系统总负荷和逐小时备用。输入校验通过，模型构建、求解和独立验解状态均为 `not_run`。 [正式输入](input.json) · [数据检查报告](../../reports/kazarlis1996_uc60_inputs_v1/data_validation.json)

## 基础信息

| 项目 | 内容 |
| --- | --- |
| 算例与版本 | `kazarlis1996_uc60_inputs_v1`，发行版 1.0.0，profile `kazarlis1996-table-inputs/0.1.0` |
| 分类 | 系统级火电 UC 输入 `system_aggregate_uc_inputs`，同属 `kazarlis1996` 文献家族 |
| 来源 | Kazarlis、Bakirtzis、Petridis（1996），Table II 的基础机组参数及已登记输入与备用规则。 [论文 DOI](https://doi.org/10.1109/59.485989) · [来源记录](provenance.json) |
| 数据版本 | 按 10 台基础参数块扩展的 60 台派生输入，复制倍数 6 |
| 机组与容量 | 60 台。机组最大出力合计 9,972 MW，最小出力合计 2,640 MW |
| 系统负荷 | 第 12 小时达到峰值 9,000 MW，24 小时负荷电量 162,600 MWh |
| 时间范围 | 相对时段第 1–24 小时，步长 1 小时。输入未给定日历日期或时区 |
| 节点、线路与潮流 | 负荷按系统总量记录，当前数据表未提供节点和线路参数。物理节点数、线路数和潮流模型均未确定 |
| 数据完备度 | C（存在适用项缺口）。当前表未提供爬坡、初始出力、冷热切换规则和末端边界。 [缺口清单](issues.json) |
| 数据再分发许可 | `UNVERIFIED`。 [第三方通知](../../docs/profiles/kazarlis1996-table-inputs/THIRD_PARTY_NOTICES.md) |

## 机组与约束要素

| 要素 | 本例数据与规则 |
| --- | --- |
| 功率上下限 | `pmin_mw` 为 10–150 MW，`pmax_mw` 为 55–455 MW，各有 60 条记录 |
| 供需平衡 | 提供逐小时系统总负荷。当前输入按系统总量登记，模型平衡与削负荷处理待定义 |
| 常规和启停爬坡 | 当前数据表未提供常规上、下爬坡限值及启动、停机爬坡参数 |
| 最小开停时间 | `min_up_hours` 和 `min_down_hours` 各有 60 条记录，范围均为 1–8 小时 |
| 备用 | `reserve_mw` 逐小时按系统负荷的 10% 派生，峰值 900 MW。全部机组最大出力减去负荷及备用的最小余量为 72 MW，出现在第 12 小时。当前表未定义逐机组备用交付 |
| 生产费用 | 保留原表 `cost_a`、`cost_b`、`cost_c` 及字段单位。本版以原系数形式交付，具体调度目标表达式待模型定义 |
| 冷热启动 | 保留 `hot_start_cost`、`cold_start_cost` 和 `cold_start_hrs`。后者为 0–5 小时，其中 18 条记录的值为 0，沿用基础表原值。冷热切换规则及等号边界待核 |
| 停机费用 | 当前数据表未提供 |
| 初始状态与出力 | `initial_status_hours` 保留初始连续开停时间及正负号，12 台初始开机、48 台初始停机。当前数据表未提供初始出力 |
| 末端边界 | 当前数据表未提供末端状态要求 |

## 输入与复核

使用 [10 台基础算例](../kazarlis1996_uc10_inputs_v1/README.md) 的完整机组参数块共 6 份，连续重编机组 ID。每台机组的参数和初始状态符号保留原值，`source_unit_id` 和 `copy_index` 记录原机组及复制位置。逐小时系统总负荷及备用乘 6，时段仍为第 1–24 小时。60 台输入的来源身份登记为按已记录规则构造的派生算例。

结构与 Schema、机组映射、时序和备用检查均已通过。容量检查只覆盖全部机组最大出力能否容纳负荷与备用。模型可行性、调度最优性和 Gurobi、COPT、UnitCommitment.jl 导入状态仍待实际运行验证。 [正式输入](input.json) · [字段与复核命令](../../docs/profiles/kazarlis1996-table-inputs/README.md) · [数据检查报告](../../reports/kazarlis1996_uc60_inputs_v1/data_validation.json) · [逐例 SHA-256 清单](../../reports/kazarlis1996_uc60_inputs_v1/checksums.sha256)

## 来源与许可

S. A. Kazarlis、A. G. Bakirtzis、V. Petridis，*A Genetic Algorithm Solution to the Unit Commitment Problem*，IEEE Transactions on Power Systems 11(1)，83–92，1996。原论文 PDF 与中间工作簿的身份及哈希记录见来源文件。原论文 PDF 未收录于本库。表格数据再分发许可为 `UNVERIFIED`，原作者及 IEEE 权利见第三方通知。 [论文 DOI](https://doi.org/10.1109/59.485989) · [来源记录](provenance.json) · [第三方通知](../../docs/profiles/kazarlis1996-table-inputs/THIRD_PARTY_NOTICES.md)
