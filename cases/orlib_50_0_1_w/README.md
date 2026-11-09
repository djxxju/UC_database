# OR-Library 50_0_1_w

本例为 UnitCommitment.jl 0.4 实例目录发布的 OR-Library 转换实例，采用 0.3 JSON 格式。单节点、50 台机组、24 个一小时时段，保留原负荷和显式零旋转备用。

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
