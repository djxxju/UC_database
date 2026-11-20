# Kazarlis 1996：60台、24小时输入整理版

- case_id：kazarlis1996_uc60_inputs_v1；发行版1.0.0；profile：kazarlis1996-table-inputs/0.1.0。
- 分类：系统级火电UC输入（system_aggregate_uc_inputs）；文献家族kazarlis1996。未提供网络表，不编造物理节点/线路数量。
- 来源：Kazarlis、Bakirtzis、Petridis（1996），[DOI](https://doi.org/10.1109/59.485989)，Table II及已登记的备用比例；原PDF与工作簿身份见[来源记录](provenance.json)。
- 由10台基础块共复制6份，24小时负荷及备用乘6；本轮未把规则展开冒充作者原生电子文件或逐规模论文重验。

## 文件与边界

[input.json](input.json)为完整输入；[issues.json](issues.json)保留当前表五类缺口及未核许可；[检查报告](../../reports/kazarlis1996_uc60_inputs_v1/data_validation.json)与[哈希清单](../../reports/kazarlis1996_uc60_inputs_v1/checksums.sha256)记录实际检查。单位、复制关系及未提供规则见[共享profile](../../docs/profiles/kazarlis1996-table-inputs/README.md)。

原11项机组参数保留，成本a/b/c不转换成折点；初始时长符号及cold_start_hrs零值不变。备用数值是负荷10%的派生值。缺口不填0、不确定冷热启动切换或末端规则。结构、复制和容量必要条件通过，最小余量72MW（第12小时）；未执行模型构建、求解、独立验解、Gurobi/COPT/UC.jl导入测试，不宣称可行或最优，不包含results目录。

## 权利与引用

再分发许可仍为UNVERIFIED，不能当作开放许可确认。原论文PDF不随包分发；仓库许可不自动覆盖原作者/IEEE权利。详见[第三方通知](../../docs/profiles/kazarlis1996-table-inputs/THIRD_PARTY_NOTICES.md)。
