# 邓俊2015含爬坡输入 profile 1.0.0

来源：邓俊等《一种含四类0-1变量的机组组合混合整数线性规划模型》。本组是基于Kazarlis的文献修改版，共10/20/40/60/80/100台六规模、24小时，按系统级火电UC输入分类。统一为一个文献基准家族，不将前后文献重复计为两个家族；基础参数和后续补充分别溯源。

## 字段、单位和规则

基础字段来自Kazarlis1996 Table II：

| 字段 | 含义 | 单位 |
| --- | --- | --- |
| id | 本规模机组编号，1至N | 1 |
| pmax_mw / pmin_mw | 最大/最小实际出力 | MW |
| cost_a / cost_b / cost_c | 二次生产费用A/B/C系数 | $/h、$/MWh、$/(MW²·h) |
| min_up_hours / min_down_hours | 最小开/停机时长 | h |
| hot_start_cost / cold_start_cost | 热/冷启动费用 | $ |
| cold_start_hrs | 原表cold start时间参数；冷热切换按下述邓俊规则 | h |
| initial_status_hours | 初始连续开机为正、停机为负 | h |
| source_unit_id / copy_index | 基础机号1至10 / 复制块编号 | 1 |

time_series中hour为1至24，demand_mw为系统总负荷，reserve_mw为0.1×负荷，均为MW；time_step_hours=1、horizon_hours=24。基础cold_start_hrs等不改用引用[14]中的其他数值。基础文献来源、固定历史输入和原件哈希见[source_mapping.json](source_mapping.json)。

邓俊2015补充以下字段：

| 字段 | 含义 | 单位 |
| --- | --- | --- |
| initial_p | 第1时段之前的实际初始出力 | MW |
| ramp_up / ramp_down | 在线升/降出力变化率上限 | MW/h |
| pstart / pshut | 启动时段、停机前时段的出力上限 | MW |

1–7机升降爬坡分别225、225、50、50、60、60、60 MW/h；启停上限均为各自Pmin。8–10机升降爬坡135 MW/h、启动45 MW、停机35 MW。135高于Pmax55并不矛盾，实际出力仍受Pmax约束。1/2初始455/245 MW，其余由原始停机状态和式(11)得到0。完整数值来源与单位标签差异见[source_mapping.json](source_mapping.json)。

初始连续开停时长保留正负号。生产费用为A*u+B*p+C*p²，p是实际MW；系数原样保存，未改为分段折点。论文采用分段MILP后IPOPT经济调度，本组没有运行或复现此流程。整数停机时长d在min_down_hours至min_down_hours+cold_start_hrs（含）时热启动，达到min_down_hours+cold_start_hrs+1时冷启动（3.2节）。不从引用[14]替换冷热启动时间等其他字段。

备用按系统总量为负荷10%，对应式(10)容量口径；不加入响应时长或爬坡交付假设。网络参数未提供，不制造物理节点/线路数。约束时间范围见2.3；时域外末端状态要求未核明，保留待核，不补末端约束或停机费用。

## 规模展开和检查

N台完整复制10台块N/10次，source_unit_id标基础机号，copy_index标副本号。单台参数与初始出力均不放大，仅每小时负荷和备用乘倍数。此为项目明确派生规则，不能计为独立物理电网或声称逐规模作者原件复现。

安装jsonschema后，在仓库根运行`python scripts/deng2015/validate_inputs.py`。检查Schema、参数/单位、初始出力一致性、启停上限、复制、负荷/备用、容量必要界及哈希。报告分别记录源字段核查、输入检查、求解、独立验解；后两项均not_run。必要条件通过不等于UC可行。本文4.4的无爬坡对比结果不作为本组含爬坡版的已复现结果。

数据再分发许可仍UNVERIFIED，见[第三方通知](THIRD_PARTY_NOTICES.md)。
