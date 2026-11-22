# OR-LIB 10机组24小时输入版

本例为UnitCommitment.jl发布的`or-lib/10_0_1_w`转换表示：10台机组、1节点、24个一小时时段、1个日实例，无输电线路。未从长时序截取，不指定日历日期；不是RTS24。

## 基础信息

| 项目 | 内容 |
| --- | --- |
| 来源与版本 | UnitCommitment.jl 0.4 实例目录的 [OR-Library 10_0_1_w](https://axavier.org/UnitCommitment.jl/0.4/instances/or-lib/10_0_1_w.json.gz)，原 JSON 格式为 `0.3`。原 gzip 和解压 JSON 的 SHA-256 见[来源记录](provenance.json)。 |
| 许可 | 原 JSON 内嵌的 [MIT 通知](LICENSE.txt)。 |
| 网络与设备 | 1 个母线 `b1`，10 条发电机组记录，均接入该母线。无输电支路，线路潮流与网络安全约束不适用。 |
| 机组容量 | 最大出力合计 1,771 MW，各机组最小出力合计 548 MW，均由生产费用曲线首末出力折点汇总。时域开始前已在线 6 台。 |
| 时域与负荷 | 1 个日实例，24 个 1 小时时段。第 12 小时峰值 1,453.913382 MW，24 小时需求电量 28,140.113949 MWh。自然日日期未给出。 |
| 数据完备度 | B（明确简化型，限本文计算 profile）。明确的单节点、显式零备用和单档启动，按已核读取默认和公布计算规则执行。费用币种和价格年待核。 [缺口清单](issues.json) |
| 执行证据 | [历史输入校验](../../reports/ucjl_orlib_10_0_1_w_native_v1/data_validation.json)记录 13 项通过。[参考运行与独立验解](../../results/ucjl_orlib_10_0_1_w_native_v1/README.md)。Gurobi 13.0.0 和 COPT 8.0.7 均达到声明容差，独立验解通过，削负荷 0.243366 MWh。 |

## 机组与约束要素

- **源参数与费用。** 每台机组有初始开停持续时间和出力、最小开停时间、上下爬坡限值、5 个生产费用折点及 1 档启动费。合计 50 个生产费用折点、10 条启动费用记录。燃料和技术类别未给出，源费用字段标记 `$`，币种及价格基年待核。
- **开停机与爬坡。** 项目模型执行出力上下限、最小开停时间、初始剩余开停义务以及高于在线最小出力部分的爬坡限制。首小时爬坡规则对初始在线机组适用，末端开停窗口截在第 24 小时。
- **备用及平衡。** 24 个时段的旋转备用需求均为源数据显式零值。项目模型固定备用为零，并按单节点逐时平衡计入削负荷。
- **模型默认与待核。** 启停出力限额采用已核对的读取器默认值 1,000,000 MW，削负荷默认罚价为每 MWh 1,000。计算口径见[模型说明](../../scripts/orlib10/MODEL.md)，作者参考调度和匹配结果仍待核。

## 目录文件

目录保留五份文件。input.json包含完整机组、负荷、备用、费用、原引用及通知；README.md说明数据；provenance.json保留来源与哈希；issues.json列缺口；LICENSE.txt提供原许可。

数值CSV可从JSON再生，字段说明并入本页。当前input.json的易读排版与源归档分别记录哈希。数据数值保持来源精度，原历史计算记录按各自运行身份保存。

## 字段说明

| JSON字段 | 含义和单位 |
| --- | --- |
| Parameters.Time (h) / Version | 总小时数24 / 原JSON格式0.3 |
| Generators.*.Bus | 所属母线b1 |
| Production cost curve (MW) / ($) | 同索引的出力与总生产费用折点，首末出力分别为Pmin/Pmax；原费用符号$，币种/基年待核 |
| Initial status (h) | 已连续开停时长，正为开机、负为停机 |
| Initial power (MW) | 时域前的发电功率 |
| Minimum uptime (h) / Minimum downtime (h) | 最小连续开机/停机时长 |
| Ramp up limit (MW) / Ramp down limit (MW) | 原上下爬坡字段，计算口径按本例模型说明 |
| Startup costs ($) / Startup delays (h) | 同位置启动费及停机时长门槛，本例每机只有一档 |
| Reserve eligibility | 可参与的备用产品编号 |
| Buses.b1.Load (MW) | 按原顺序排列的24小时负荷 |
| Reserves.r1.Amount (MW) / Type | 备用需求数组（原值全零）/ Spinning |
| LICENSE / SOURCE | 原内嵌许可和参考引用 |

机组、母线和备用编号采用原 JSON 对象键，保留原顺序。

[历史输入检查](../../reports/ucjl_orlib_10_0_1_w_native_v1/data_validation.json) · [本轮精简核验](../../reports/ucjl_orlib_10_0_1_w_native_v1/package_validation.json) · [逐例哈希](../../reports/ucjl_orlib_10_0_1_w_native_v1/checksums.sha256) · [历史参考结果](../../results/ucjl_orlib_10_0_1_w_native_v1/README.md)

历史报告中的文件哈希和项目计算结论对应当时版本。本轮检查只读取数据及已有代码，不重新求解。
