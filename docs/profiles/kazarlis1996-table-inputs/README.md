# Kazarlis 1996 表格输入 profile 0.1.0

分类为system_aggregate_uc_inputs：系统级火电UC输入。已给机组参数、24小时系统总负荷及10%备用规则；未给网络表，不制造物理节点或线路数量。一个文献家族包含10/20/40/60/80/100台六个规模，不能计作六个独立物理电网。

## 字段与来源

input.json的generators每条包含id、pmax_mw、pmin_mw、cost_a/b/c、min_up_hours、min_down_hours、hot_start_cost、cold_start_cost、cold_start_hrs、initial_status_hours。单位在field_units中，初始连续开/停机时长保留正负号，cold_start_hrs的0保留。source_unit_id/copy_index是整理添加的复制溯源字段。

cost_a/b/c原系数原样保留，不转换为成本折点，也不在此profile补定费用公式。cold_start_hrs照原字段记录，不推定冷热启动切换阈值或等号边界。初始出力、爬坡/启停爬坡、停机费用、节点线路以及冷热启动切换/末端规则的当前表缺口见各例issues；不填0、不建立额外模型。

time_series含hour=1—24、demand_mw原负荷及reserve_mw=0.1×demand_mw派生数值。time_step_hours=1、horizon_hours=24。备用容量必要界仅检查全部机组Pmax总和能否覆盖负荷+备用，不等于可行调度、爬坡交付或N-1。

## 展开规则与身份

N台取k=N/10，完整复制10台参数块共k份，仅重编id为1—N；source_unit_id=(id−1)%10+1，copy_index=floor((id−1)/10)+1。单台参数和初始时长不乘k；每个小时的负荷及备用乘k，时间轴不变。原值与展开输入分别留源/派生身份。该规则由用户明确给定，未将本轮整理写成逐规模作者模型复现。

## 检查与使用

结构由schema/kazarlis1996-table-inputs-0.1.0.schema.json声明；数组长度与机组数的关联、复制对应和容量必要界另由scripts/kazarlis1996/validate_inputs.py核对。安装同目录requirements.txt后，从仓库根运行：

```text
python scripts/kazarlis1996/validate_inputs.py
```

只读校验器读取已发布JSON并检查Schema、复制关系、时序、逐例清单和已记录容量结果，不启动求解。报告沿用本轮真实检查；没有模型构建、求解、独立验解或求解器导入验收，全部not_run。不能套用要求分段成本/初始出力/爬坡的OR-LIB输入Schema。

论文、来源和权利状态见[第三方通知](THIRD_PARTY_NOTICES.md)。本profile的格式定义和检查范围不等于许可确认。
