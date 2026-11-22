# OR-Library 20_0_1_w 单日机组组合

本例采用 UnitCommitment.jl 0.4 实例服务器发布的 OR-Library 转换实例。JSON 内部版本为 0.3。发布方已给出 24 个一小时时段，包含单节点 b1、20 台机组、24 个负荷值和 24 个旋转备用需求值。备用需求在源文件中显式为零。模型的功率与备用均为系统口径。

## 基础信息

| 项目 | 内容 |
| --- | --- |
| 来源与版本 | UnitCommitment.jl 0.4 实例目录的 [OR-Library 20_0_1_w](https://axavier.org/UnitCommitment.jl/0.4/instances/or-lib/20_0_1_w.json.gz)，原 JSON 格式为 `0.3`。原 gzip 和解压 JSON 的 SHA-256 见[来源记录](provenance.json)。 |
| 许可 | 原 JSON 内嵌的 [MIT 通知](LICENSE.txt)。 |
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

| 文件 | 用途 |
| --- | --- |
| `input.json` | 已归档 gzip 的原字节解压结果，供程序建模。 |
| `LICENSE.txt` | 原 JSON `LICENSE` 文本的逐字节副本。 |
| `provenance.json` | 原归档 URL、实例名、时间、原 gzip/解压 JSON 哈希及原引用。 |
| `generators.csv` | 20 台机组的节点、初始状态、出力、开停机和爬坡参数。 |
| `cost_points.csv` | 100 个分段线性生产费用折点。 |
| `startup_tiers.csv` | 20 条启动费用及相应停机阈值。 |
| `hourly.csv` | 逐小时负荷和旋转备用需求，时序保留原数组顺序。 |
| `field_dictionary.csv` | CSV 列对应的 JSON 路径和单位。 |
| `issues.json` | 源数据缺省规则、待核项与不适用范围。 |

机组最小与最大出力分别来自首末生产曲线折点。CSV 小时与折点编号从 1 起，JSON 数组索引从 0 起。输入整理保留数值精度与机组顺序。

已归档原 gzip 的 SHA256 为 `6a567e0c8ebe5b2420d940f7526f343850fd45c6400e09ef1247cb450a6551be`，解压文件为 `37bf1d943664bcb9b5b74d6ff599ece16858e40750a6bcb423827e5f128e2327`。归档身份根据历史清单与本次重算确认。源引用见 `provenance.json`。 [UC.jl 固定实例入口](https://axavier.org/UnitCommitment.jl/0.4/instances/or-lib/20_0_1_w.json.gz)

结构、字段关联、时序、费用参数、容量必要条件和派生视图复核见[数据报告](../../reports/orlib_20_0_1_w/data_validation.json)。总最大出力为 3,414 MW，峰值负荷为第 12 小时的 2,389.360312 MW。结果状态以[结果目录](../../results/orlib_20_0_1_w)为准，计算口径见[模型说明](../../docs/profiles/orlib_flat_audited_defaults_uc_v1/MODEL.md)。

在仓库根目录可用 Python 3.13 和 jsonschema 4.26.0 复核输入、许可与整理视图。拿到归档原 gzip 后，可同时复核压缩字节和解压内容。添加 `--write` 会生成缺少的视图和许可副本，已有内容若与期望不一致，程序退出并指出文件。

```powershell
python reports/orlib_20_0_1_w/audit_input.py
$archiveMember = "C:/path/to/20_0_1_w.json.gz"
python reports/orlib_20_0_1_w/audit_input.py --source-gzip $archiveMember
```
