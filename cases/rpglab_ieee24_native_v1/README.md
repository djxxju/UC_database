# RPG Lab IEEE24 原模型算例 v1

算例编号：`rpglab_ieee24_native_v1`；模型规则：`rpglab-ieee24-native/1.0.0`。24节点、15条机组记录、38条物理线路、1800个独立24小时样本。原机组/线路/负荷数值及作者B-θ UC语义保持。

## 基础信息

| 项目 | 内容 |
| --- | --- |
| 来源版本 | RPG Lab GitHub 固定提交 `d9fb2a1c92c86b9d16c8fa30372b74cd3c86d89e`，原 README 标注 CC BY 4.0。[固定来源与哈希](provenance.json) |
| 节点与设备 | 24 个节点，15 条机组记录分布在 15 个节点。其中 14 条最大有功出力为正，节点 14 的 G7 为零有功记录。 |
| 装机及出力范围 | 按模型功率口径，`genD_Pmax` 合计 3,405 MW，单条 0–591 MW。全体记录的 `genD_Pmin` 合计 661.1 MW。 |
| 负荷与时域 | 每个样本独立包含 24 个一小时时段和 24 个节点。1,800 个样本共 1,036,800 个节点负荷值，未赋日历日期、时区或概率。样本 196 第 8 时段的系统负荷为全体样本峰值，约 2,169.57 MW。 |
| 完备度 | C（存在适用项缺口）。声明的范围为作者 B-θ UC。费用币种和价格年、备用响应时长的工程口径及线路参数工程基准仍待核。分类按 2026-11-22 对照现有模型说明、数据校验和缺口清单判定。[数据校验](../../reports/rpglab_ieee24_native_v1/data_validation.json) · [缺口](issues.json) |

## 网络与拓扑

24 个节点连通，38 条物理线路形成 34 组无向端点对。15–21、18–21、19–20、20–23 各保留两条物理线路。选定模型采用作者 Notebook 零基索引 30 的单元的 DC B-θ 潮流规则，固定节点 1 的相角为零。线路潮流除以 100 后等于相角差与 `branch_b` 的乘积，双向限额为 ±`branch_rateA`，正常限额为 157.5–460 MW。源字段 `branch_rateC` 保留，其适用工况待核。作者用于机器学习的 34 边图、PTDF 模型及线路 N−1 事故约束均在本次参考结果范围之外。[线路参数](branches.json) · [模型规则](../../docs/profiles/rpglab-ieee24-native/model_profile.json)

## 机组与约束要素

| 要素 | 来源字段与模型口径 |
| --- | --- |
| 出力与平衡 | `genD_Pmin` 约束在线机组的最小出力，出力与备用合计受 `genD_Pmax` 约束。各节点的本地发电加净流入必须等于节点负荷。 |
| 爬坡与最小开停 | 常规爬坡及启停出力变化沿用 `HRamp`、`StartRamp` 及作者公式，保留第 1 时段与其余时段的上爬坡写法差别。最小连续开停时间沿用 `genD_minUP`、`genD_minDN` 的循环窗口。 |
| 备用 | `SPRamp` 限制在线机组的备用能力。每个时段，总备用须覆盖任一机组的出力与其自身备用之和。`NSRamp` 原值保留，在所查 B-θ 约束中未使用。 |
| 费用 | `genC_Cost` 为线性出力费用，`genC_NLoad` 为空载费用，`genC_Startup` 为单档启动费用。选定目标未设独立停机费用或冷热启动分档。 |
| 初末边界 | 单样本第 24 时段与第 1 时段循环相接，应用于启停、最小开停和爬坡。所查模型未设固定的时域前机组状态、功率或已持续时长。 |
| 特殊设备 | G7 的零有功记录原样保留。G13 为 300 MW 记录，源表中生产、空载和启动费用均为零。有证据表明 G13 与上游水电聚合相关，选定模型按一般发电记录处理，未设水量或库存约束。设备类别与原始变换详见缺口清单。 |

## 六份文件

- [generators.json](generators.json)：机组原字段与编号。
- [branches.json](branches.json)：38条物理线路，包括并联记录。
- [demand_wide.csv.gz](demand_wide.csv.gz)：无损压缩负荷表；首列sample_id为原TXT行号1—1800，其后按t01_bus01至t24_bus24排列。单位和口径见共享字典。
- issues.json：缺口、适用限制及当前执行状态；不补造参数。
- provenance.json：固定来源、版本、许可、引用、哈希和转换说明。
- README.md：本说明。

共享[字段字典](../../docs/profiles/rpglab-ieee24-native/field_dictionary.json)与[模型规则](../../docs/profiles/rpglab-ieee24-native/model_profile.json)保留原成本、每机组备用、爬坡及24→1循环边界。不能替换成无网络UC。

## 当前质量状态

数据层65项检查通过。1800样本均达到COPT相对gap0.01%，并通过独立约束/二元/目标验算。见[数据检查](../../reports/rpglab_ieee24_native_v1/data_validation.json)、[参考总表](../../results/rpglab_ieee24_native_v1/reference_results.csv)和[验解摘要](../../results/rpglab_ieee24_native_v1/verification.json)。达到声明容差不等于零gap精确最优，不认证N-1、作者PTDF或AI标签复现；费用币种及价格年尚未确认。

读取输入只需Python标准库：JSON用json.load，压缩CSV用gzip.open(..., 'rt', encoding='utf-8')与csv.DictReader。负荷值未舍入、未打乱，sample_id不因求解重排。

## 来源与复算

来源为rpglab/GNN-LSTM_C-V-R-SCUC，固定提交d9fb2a1c92c86b9d16c8fa30372b74cd3c86d89e。CC BY 4.0（原README）；引用Arun Venkatesh Ramesh与Xingpeng Li，Spatio-Temporal Deep Learning-Assisted Reduced Security-Constrained Unit Commitment，DOI 10.1109/TPWRS.2023.3313430。精确URL和文件哈希见provenance。

本库不重复上传原件缓存、完整调度变量和逐次运行日志。重新源值对照或求解前，先按仓库README在独立目录恢复固定版本原件。公布的参考总表是已验证结果摘要，未附候选变量，使用者不能仅凭本表重算每个候选约束。

验解摘要中的发布来源哈希对应[当时的来源记录](https://github.com/djxxju/UC_database/blob/e72c0ca0179398045685f5daee4ea597d75cd981/cases/rpglab_ieee24_native_v1/provenance.json)，当前说明及来源记录见[逐例 SHA-256 清单](../../reports/rpglab_ieee24_native_v1/checksums.sha256)。
