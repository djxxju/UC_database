# 输入分类

分类通过catalog.json的family以及README章节表达；实际文件继续遵守cases/<case_id>与reports/<case_id>，不嵌套另一级类别目录。

| family | 含义 |
|---|---|
| network_uc | 带网络输入的UC算例，具体求解状态逐例登记 |
| network_uc_inputs | 已整理的网络UC输入，模型/执行边界见profile |
| single_bus_uc | 已明确单节点表示的UC系列，例如现有OR-LIB三例 |
| system_aggregate_uc_inputs | 机组参数与系统总负荷输入，无网络表；不推定物理节点数，当前新增Kazarlis六规模 |

case_count按实例条目计；system_count按已识别物理基础电网计。Kazarlis六规模为1个文献基准家族，不增加物理电网计数，也不并入OR-LIB来源。输入整理通过、Schema通过、模型/求解/验解分别记状态。
