# IEEE24 legacy 33-record selected inputs

**Input organization only**: 24 bus records, 33 generator records, 38 branch records and 1500 load rows, each with 576 source-position values. This is a distinct version from [the published 15-record case](../rpglab_ieee24_native_v1/README.md); not an additional physical system.

## 基础信息

| 项目 | 内容 |
| --- | --- |
| 来源版本 | RPG Lab Figshare 数据集 V2，DOI `10.6084/m9.figshare.24116394.v2`，归档文件 ID `42307935`。Figshare V2 数据集元数据标注 CC BY 4.0，已按 SHA-256 核对本例所选的两份归档成员。[来源及许可证据](provenance.json) · [来源核对](../../reports/rpglab_ieee24_legacy33_inputs_v1/source_verification.json) |
| 节点与设备 | 24 个节点，33 条机组记录分布在 11 个节点。其中 32 条最大有功出力为正，节点 14 有一条零有功记录。节点 22 有 6 条 `genD_Pmax` 为 50 且成本字段为零的记录。对应设备类型待核。 |
| 出力字段 | `genD_Pmax` 原数值合计 3,405，单条 0–400。`genD_Pmin` 原数值合计 974.85，单条 0–140。单位及旧模型约束用法待核。 |
| 负荷与时域 | 1,500 行各保留 576 个源列位置，共 864,000 个数值。按时段在外、节点在内解释为每行 24 时段 × 24 节点，是有数值诊断支持的候选映射。列顺序定义、时段长度和旧模型配对仍待核。[候选映射](../../docs/profiles/rpglab-ieee24-legacy33-inputs/mapping.json) |
| 完备度 | D（关键语义待核）。所选输入的来源身份与逐值保留已核对。正式时段映射、单位、成本和初末边界尚未闭合，模型构建、求解和独立验解未执行。分类按 2026-11-22 对照现有输入审查及缺口清单判定。[输入校验](../../reports/rpglab_ieee24_legacy33_inputs_v1/data_validation.json) · [独立逐值核对](../../reports/rpglab_ieee24_legacy33_inputs_v1/independent_review.json) · [缺口](issues.json) |

## 网络与拓扑

24 个节点连通，38 条物理线路形成 34 组无向端点对。15–21、18–21、19–20、20–23 各有两条线路。与本库原模型版逐行比较，线路端点、`branch_b`、`branch_rateA` 和 `branch_rateC` 的数值一致。旧版另保留源字段 `branch_radial`。旧版潮流方程、参考节点、工程基准、两套限额的适用工况及 N−1 规则仍待核。[旧版线路表](branches.csv) · [原模型版线路表](../rpglab_ieee24_native_v1/branches.json)

## 机组与约束要素

| 要素 | 已保留数据及适用缺口 |
| --- | --- |
| 功率与平衡 | 机组表提供 `genD_Pmax`、`genD_Pmin` 和接入节点。旧版出力约束、节点平衡定义及正式负荷列对应关系待核。 |
| 爬坡、最小开停及备用 | 保留 `HRamp`、`StartRamp`、`SPRamp`、`NSRamp`，具体单位及旧模型用途待核。`genD_minUP`、`genD_minDN` 的原数值均为 1–48。所选输入未给单独的备用需求曲线，需求与交付规则待核。 |
| 费用 | 保留单列 `genC_Startup`、`genC_Cost`、`genC_NLoad`。所选输入未确定冷热启动分档或阈值、停机费用规则、成本函数及单位。 |
| 初末边界 | `genD_status` 的 33 个保留值均为 1，编码含义待核。初始状态、初始出力、已连续开停时长及终末边界均待核。 |
| 特殊设备 | 节点 14 的零容量记录及节点 22 的六条同容量记录均保留。设备类别及水电、风光、储能等专项约束仍缺少旧版语义证据。 |

Files: [buses.csv](buses.csv), [generators.csv](generators.csv), [branches.csv](branches.csv) and [demand.csv.gz](demand.csv.gz). CSVs use UTF-8 BOM. Numeric text, record order and source line positions are preserved. The load headers source_col_001..576 deliberately identify positions, not certified time/bus labels. Decompress demand.csv.gz before opening in Excel or read it with Python gzip + csv.

Scope excludes LOAD blocks and embedded arrays in the composite source file, and excludes author commitments/dispatch/flows. Independent comparison preserved 738 static parameters + 95 record IDs and 864000 load values. It does not certify full UC semantics, units, source authenticity, solver compatibility, feasibility or optimality. No new solving was performed.

[Field dictionary](../../docs/profiles/rpglab-ieee24-legacy33-inputs/field_dictionary.csv) · [Mapping](../../docs/profiles/rpglab-ieee24-legacy33-inputs/mapping.json) · [Input checks](../../reports/rpglab_ieee24_legacy33_inputs_v1/data_validation.json) · [Independent comparison](../../reports/rpglab_ieee24_legacy33_inputs_v1/independent_review.json) · [Issues](issues.json)

Source attribution: Arun Venkatesh Ramesh and Xingpeng Li, *Spatio-Temporal Deep Learning-Assisted Reduced Security-Constrained Unit Commitment*, Figshare dataset V2, DOI [10.6084/m9.figshare.24116394.v2](https://doi.org/10.6084/m9.figshare.24116394.v2). Publisher metadata identifies CC BY 4.0; [license](https://creativecommons.org/licenses/by/4.0/). Changes: selected tables split into CSV; row/line metadata added; numeric tokens retained; load compressed without changing decompressed CSV bytes. Both selected local source files were independently matched by exact SHA256 to the named members of Figshare V2 archive file 42307935 on 2026-11-01; see reports source_verification.json. The whole ZIP MD5 was not recomputed. This verifies selected file identity, not full model semantics or all underlying third-party rights.

[来源记录](provenance.json) · [逐例 SHA-256 清单](../../reports/rpglab_ieee24_legacy33_inputs_v1/checksums.sha256)
