# OR-Library 50_0_1_w

本例为 UnitCommitment.jl 0.4 实例目录发布的 OR-Library 转换实例，采用 0.3 JSON 格式。单节点、50 台机组、24 个一小时时段，保留原负荷和显式零旋转备用。

## 基础信息

| 项目 | 内容 |
| --- | --- |
| 来源与版本 | UnitCommitment.jl 0.4 实例目录的 [OR-Library 50_0_1_w](https://axavier.org/UnitCommitment.jl/0.4/instances/or-lib/50_0_1_w.json.gz)，原 JSON 格式为 `0.3`。原 gzip 和解压 JSON 的 SHA-256 见[来源记录](provenance.json)。 |
| 许可 | 原 JSON 内嵌的 [MIT 通知](LICENSE.txt)。 |
| 网络与设备 | 1 个母线 `b1`，50 条发电机组记录，均接入该母线。无输电支路，线路潮流与网络安全约束不适用。 |
| 机组容量 | 最大出力合计 8,603 MW，各机组最小出力合计 2,738 MW，均由生产费用曲线首末出力折点汇总。时域开始前已在线 27 台。 |
| 时域与负荷 | 1 个日实例，24 个 1 小时时段。第 12 小时峰值 6,575.280994 MW，24 小时需求电量 127,262.847096 MWh。自然日日期未给出。 |
| 数据完备度 | B（明确简化型，限本文计算 profile）。明确的单节点、显式零备用和单档启动，按已核读取默认和公布计算规则执行。费用价格年待核。 [缺口清单](issues.json) |
| 执行证据 | [历史输入校验](../../reports/orlib_50_0_1_w/data_validation.json)记录 21 项通过。[参考运行与独立验解](../../results/orlib_50_0_1_w/README.md)。COPT 8.0.7 相对 gap 为 0.00996002%，低于 0.01% 门槛，独立验解通过，削负荷在容差内为零。 |

## 机组与约束要素

- **源参数与费用。** 每台机组有初始开停持续时间和出力、最小开停时间、上下爬坡限值、5 个生产费用折点及 1 档启动费。合计 250 个生产费用折点、50 条启动费用记录。燃料和技术类别未给出，源费用字段标记 `$`，币种及价格基年待核。
- **开停机与爬坡。** 项目模型执行出力上下限、最小开停时间、初始剩余开停义务以及高于在线最小出力部分的爬坡限制。首小时爬坡规则对初始在线机组适用，末端开停窗口截在第 24 小时。
- **备用及平衡。** 24 个时段的旋转备用需求均为源数据显式零值。项目模型固定备用为零，并按单节点逐时平衡计入削负荷。
- **模型默认与待核。** 启停出力限额采用已核对的读取器默认值 1,000,000 MW，削负荷默认罚价为每 MWh 1,000。计算口径见[模型说明](../../docs/profiles/orlib_flat_audited_defaults_uc_v1/MODEL.md)，作者参考调度和匹配结果仍待核。

- [input.json](input.json) 是原始 gzip 解压后的原字节。原 gzip 的固定来源、SHA256、项目归档和论文引用见 [provenance.json](provenance.json)。本例随附源内嵌的 [MIT 通知](LICENSE.txt)。
- [generators.csv](generators.csv)、[cost_points.csv](cost_points.csv)、[startup_tiers.csv](startup_tiers.csv) 和 [hourly.csv](hourly.csv) 是源值的表格视图。[字段字典](field_dictionary.csv)列出单位和原字段。
- [计算 profile](../../docs/profiles/orlib_flat_audited_defaults_uc_v1/MODEL.md)定义爬坡、成本、边界和零备用的处理。[问题清单](issues.json)列出读取器默认项、适用范围和待核实信息。
- [输入校验](../../reports/orlib_50_0_1_w/data_validation.json)和[逐例 SHA256](../../reports/orlib_50_0_1_w/checksums.sha256)可用于检查文件及数据一致性。[参考运行与复跑方法](../../results/orlib_50_0_1_w/README.md)记录求解及独立验解。

在仓库根目录使用 Python 3.13 和 `jsonschema==4.26.0` 检查输入。首条命令检查随包 JSON、MIT 通知、Schema 和 CSV。若已从来源取得 gzip，可在首条命令附加 `--source-gzip <路径>`，再核对其 SHA256 及解压字节。第二条命令在临时副本中注入五项故障，验证对应规则能识别错误。

```text
python -B scripts/orlib50/audit_orlib50_input.py
python -B scripts/orlib50/test_audit_orlib50_input.py
```

容量筛查仅覆盖逐时负荷加备用需求与总最大出力的关系。作者结果身份和费用币值基年仍待核实。
