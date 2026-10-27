# RPG Lab IEEE24 原模型算例 v1

算例编号：`rpglab_ieee24_native_v1`；模型规则：`rpglab-ieee24-native/1.0.0`。24节点、15条机组记录、38条物理线路、1800个独立24小时样本。原机组/线路/负荷数值及作者B-θ UC语义保持。

## 六份文件

- generators.json：机组原字段与编号。
- branches.json：38条物理线路，包括并联记录。
- demand_wide.csv.gz：无损压缩负荷表；首列sample_id为原TXT行号1—1800，其后按t01_bus01至t24_bus24排列。单位和口径见共享字典。
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
