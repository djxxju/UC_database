# OR-LIB 10机组24小时输入版

本例为UnitCommitment.jl发布的`or-lib/10_0_1_w`转换表示：10台机组、1节点、24个一小时时段、1个日实例，无输电线路。未从长时序截取，不指定日历日期；不是RTS24。

`input.json`为原gzip的逐字节解压副本，包含原LICENSE、SOURCE、Parameters、Generators、Buses、Reserves。原格式Version=0.3，未改成0.4。完整许可同时保存在LICENSE.txt；来源、引用和SHA256见provenance.json。

保留50个生产成本折点、初始开停持续时间和出力、最小开停时间、爬坡限值及启动成本。原24个旋转备用需求均为0，按真实零值保留。

[字段与范围](../../docs/profiles/ucjl-orlib-native/1.0.0/README.md) · [结构Schema](../../schema/ucjl-orlib-native-1.0.0.input.schema.json) · [检查报告](../../reports/ucjl_orlib_10_0_1_w_native_v1/data_validation.json) · [未确认项](issues.json)

2026-11-06已完成本项目模型的Gurobi/COPT双求解与独立验解，总目标均1929392.436364，开停机安排一致。**含0.243366 MWh削负荷，不是全天需求全部满足。** 结果不是作者软件完整复现。

[结果与限制](../../results/ucjl_orlib_10_0_1_w_native_v1/README.md) · [运行代码](../../scripts/orlib10/README.md) · [精确模型规则](../../scripts/orlib10/MODEL.md)。原JSON未改，源缺省规则在模型说明中单独记录。
