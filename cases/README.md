# 算例输入

每个已纳入目录的算例独立保存为`cases/<case_id>/`，case_id与catalog.json逐项一致。按编号查找即可；模型类别和profile写在索引中，不再嵌套节点规模/类型/日期等多层目录。

通用要求：README.md说明规模、时长、模型及状态；provenance.json记录固定来源、许可、引用、输入/转换身份；issues.json标注缺失、歧义和适用范围。具体输入文件名及字段由对应profile决定。当前IEEE24为generators.json、branches.json、demand_wide.csv.gz；其他模型可有units.json、stochastic.json等，不强行套成同一接口。

一行负荷样本不是一个独立系统。只有参数或模型含义变化时才另建变体或主版本，不复制同一系统的1800个日样本为1800个算例目录。模板见[templates/case](../templates/case/README.md)，流程见[入库说明](../docs/contributing.md)。
