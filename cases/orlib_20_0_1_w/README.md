# OR-Library 20_0_1_w 单日机组组合

本例采用 UnitCommitment.jl 0.4 实例服务器发布的 OR-Library 转换实例。JSON 内部版本为 0.3。发布方已给出 24 个一小时时段，包含单节点 b1、20 台机组、24 个负荷值和 24 个旋转备用需求值。备用需求在源文件中显式为零。模型的功率与备用均为系统口径。

## 基础信息

| 项目 | 内容 |
| --- | --- |
| 来源与版本 | UnitCommitment.jl 0.4 实例目录的 [OR-Library 20_0_1_w](https://axavier.org/UnitCommitment.jl/0.4/instances/or-lib/20_0_1_w.json.gz)，原 JSON 格式为 `0.3`。原 gzip 和解压 JSON 的 SHA-256 见[来源记录](provenance.json)。 |
| 许可 | 原 JSON 内嵌的 [MIT 许可正文](input.json)（`LICENSE` 字段）。 |
| 网络与设备 | 1 个母线 `b1`，20 条发电机组记录，均接入该母线。无输电支路，线路潮流与网络安全约束不适用。 |
| 机组容量 | 最大出力合计 3,414 MW，各机组最小出力合计 1,033 MW，均由生产费用曲线首末出力折点汇总。时域开始前已在线 11 台。 |
| 时域与负荷 | 1 个日实例，24 个 1 小时时段。第 12 小时峰值 2,389.360312 MW，24 小时需求电量 46,245.445075 MWh。自然日日期未给出。 |
| 数据完备度 | B（明确简化型，限本文计算 profile）。明确的单节点、显式零备用和单档启动，按已核读取默认和公布计算规则执行。费用价格年待核。 [缺口清单](issues.json) |
| 执行证据 | [历史输入校验](../../reports/orlib_20_0_1_w/data_validation.json)记录 21 项通过。[参考运行与独立验解](../../results/orlib_20_0_1_w/README.md)。COPT 8.0.7 在 120 秒时限获得通过独立验解的候选，相对 gap 为 0.0869371%，削负荷在容差内为零。 |

## 机组与约束要素

- **源参数与费用。** 每台机组有初始开停持续时间和出力、最小开停时间、上下爬坡限值、5 个生产费用折点及 1 档启动费。合计 100 个生产费用折点、20 条启动费用记录。燃料和技术类别未给出，源费用字段标记 `$`，币种及价格基年待核。
- **开停机与爬坡。** 项目模型执行出力上下限、最小开停时间、初始剩余开停义务以及高于在线最小出力部分的爬坡限制。首小时爬坡规则对初始在线机组适用，末端开停窗口截在第 24 小时。
- **备用及平衡。** 24 个时段的旋转备用需求均为源数据显式零值。项目模型固定备用为零，并按单节点逐时平衡计入削负荷。
- **模型默认与待核。** 启停出力限额采用已核对的读取器默认值 1,000,000 MW，削负荷默认罚价为每 MWh 1,000。计算口径见[模型说明](../../docs/profiles/orlib_flat_audited_defaults_uc_v1/MODEL.md)，作者参考调度和匹配结果仍待核。

## 目录文件

目录保留四份文件：`input.json` 包含完整数据、原引用及完整许可；`README.md` 说明字段与用途；`provenance.json` 记录来源与哈希；`issues.json` 列出缺口。

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


机组、母线和备用编号采用原JSON对象键，保留原顺序。按需导出CSV时，point_index、tier_index及hour从1编号，对应原数组索引加1；reserve_ids按原资格数组顺序用竖线分隔；Pmin/Pmax取生产费用曲线的首末出力。

## 校验和按需表格

默认校验不要求数值CSV，已存在的CSV会逐字节核对。需要表格时可用--write导出；--source-gzip可额外比较原始归档哈希、严格解析值和顺序。

```text
python -B reports/orlib_20_0_1_w/audit_input.py
python -B reports/orlib_20_0_1_w/audit_input.py --write
python -B reports/orlib_20_0_1_w/audit_input.py --source-gzip path/to/20_0_1_w.json.gz
```

[历史输入检查](../../reports/orlib_20_0_1_w/data_validation.json) · [本轮精简核验](../../reports/orlib_20_0_1_w/package_validation.json) · [逐例哈希](../../reports/orlib_20_0_1_w/checksums.sha256) · [历史参考结果](../../results/orlib_20_0_1_w/README.md)

历史报告中的文件哈希和项目计算结论对应当时版本。本轮检查只读取数据及已有代码，不重新求解。
