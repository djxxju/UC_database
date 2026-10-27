# 参考结果

按`results/<case_id>/`保存，编号与cases、reports和catalog一致。

已真实求解后才加入reference_results.csv、verification.json和README.md。逐样本表保留求解状态、目标/界/gap、时间和验解残差；验解摘要保留参数、工具身份和实际覆盖。没有求解则在索引标记not_run，不创建虚假的零成本/零残差结果。

完整调度变量和原始LP/日志为本地工作材料，本库默认只分发有用的参考总表和摘要；需要完整变量的研究扩展另行记录范围。不把求解器状态、独立候选可行性和精确最优性混为一谈。
