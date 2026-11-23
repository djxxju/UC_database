# 邓俊2015 含爬坡100台24小时算例

| 项目 | 内容 |
| --- | --- |
| 算例 | `deng2015_uc100_ramp_inputs_v1` |
| 文献 | 邓俊等(2015)《一种含四类0-1变量的机组组合混合整数线性规划模型》，基于Kazarlis修改 |
| 分类 | 系统级火电UC输入；节点信息未提供；完备度C |
| 规模与容量 | 100台，最大出力合计16,620 MW，最小出力合计4,400 MW |
| 负荷 | 24小时，1小时步长；峰值15,000 MW；电量271,000 MWh |
| 数据版本 | 10台文献修改版的10倍规模；单机参数不缩放 |
| 输入与规则 | [input.json](input.json) · [共享字段与模型规则](../../docs/profiles/deng2015-4bin-ramp-inputs/README.md) |
| 来源与待核项 | [provenance.json](provenance.json) · [issues.json](issues.json) |
| 检查与状态 | 输入限定检查通过；容量最小余量120 MW；未求解、未验解 |
| 权利 | 数据再分发许可UNVERIFIED |

包含出力上下限、初始状态与出力、在线爬坡、启停出力上限、最小开停时间、二次生产费用、冷热启动及10%备用。启停参数按邓俊4.1，前7机爬坡按其引用[14]；没有将[14]的其他机组参数替换进来。没有节点/线路或潮流输入。

本例属于含爬坡输入版，论文无爬坡对比结果另属实验场景。容量必要条件通过不证明完整UC可行。末端要求见待核项。

[数据检查](../../reports/deng2015_uc100_ramp_inputs_v1/data_validation.json) · [哈希清单](../../reports/deng2015_uc100_ramp_inputs_v1/checksums.sha256) · [基础参数出处](../../docs/profiles/deng2015-4bin-ramp-inputs/source_mapping.json)
