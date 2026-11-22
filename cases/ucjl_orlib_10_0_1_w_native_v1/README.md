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

`input.json`为原gzip的逐字节解压副本，包含原LICENSE、SOURCE、Parameters、Generators、Buses、Reserves。原格式Version=0.3，未改成0.4。完整许可同时保存在LICENSE.txt；来源、引用和SHA256见provenance.json。

保留50个生产成本折点、初始开停持续时间和出力、最小开停时间、爬坡限值及启动成本。原24个旋转备用需求均为0，按真实零值保留。

[字段与范围](../../docs/profiles/ucjl-orlib-native/1.0.0/README.md) · [结构Schema](../../schema/ucjl-orlib-native-1.0.0.input.schema.json) · [检查报告](../../reports/ucjl_orlib_10_0_1_w_native_v1/data_validation.json) · [未确认项](issues.json)

2026-11-06已完成本项目模型的Gurobi/COPT双求解与独立验解，总目标均1929392.436364，开停机安排一致。**含0.243366 MWh削负荷，不是全天需求全部满足。** 结果不是作者软件完整复现。

[结果与限制](../../results/ucjl_orlib_10_0_1_w_native_v1/README.md) · [运行代码](../../scripts/orlib10/README.md) · [精确模型规则](../../scripts/orlib10/MODEL.md)。原JSON未改，源缺省规则在模型说明中单独记录。
