# 本次计算 profile 的源语义证据

核查日期：2026-11-05。执行者：真实子Agent audit_orlib_semantics，继承当前模型配置。只读核查官方固定提交 `e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a`；未运行Julia读取器。本文为公式及计算选择证据，不宣称完整UC.jl软件复现、论文目标复现或独立可行性验收。

本次选择：source-default selected profile。保留原数值、above-minimum爬坡、初始条件、截断终末窗口及1000削负荷；利用本例SU/SD冗余和零备用可行投影作简化。

## 原输入读取与迁移

- [instance/migrate.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/instance/migrate.jl)：`_migrate_to_v04`（41–49行）为没有Type的0.3机组补`Thermal`。不修改本例生产参数。
- [instance/read.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/instance/read.jl)：接受`Time (h)`，缺省`Time step (min)=60`（160行）。缺省SU/SD均`1e6 MW`（319–320行）。缺省Must run为false、commitment status未固定。原输入保持Version=0.3，不改成0.4。
- [validation/repair.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/validation/repair.jl)：只处理非递增启动档、下降启动费用、非凸生产成本及SU低于Pmin。本例单启动档且曲线凸、SU=1e6，不触发这些修复。没有实际调用Julia repair的运行证据。

## 符号、出力和成本

以1开始计时，T=24；u为开机，v为启动，w为停机。q是最小出力以上部分，实际出力P=Pmin*u+q。原成本曲线第一个点费用乘u，其余按出力段斜率计费；启动单档费用乘v。负荷削减记s。

状态转换：u[t]-u[t-1]=v[t]-w[t]，v[t]+w[t]<=1。t=1的前序状态为初始持续时间的符号。见[Gar1962/status.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/Gar1962/status.jl)。

## 默认MorLatRam2013爬坡的精确本例形式

[base/structs.jl:44](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/base/structs.jl#L44)指定默认MorLatRam2013.Ramping。

公式直接来自[MorLatRam2013/ramp.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/MorLatRam2013/ramp.jl)。本例Pmin在时间上不变，reserve总量记r：

- t=1且初始在线：q[1]+r[1] <= P0-Pmin+RU；q[1] >= P0-Pmin-RD。
- t=1且初始离线：不加入这两条初始爬坡约束。不是把前序q设0后强制相同公式。
- 对所有t=2..T，无论启停状态：q[t]+r[t]-q[t-1] <= RU；q[t-1]+r[t-1]-q[t] <= RD。
- 这些恒定Pmin公式右边是RU/RD常数，没有u、v、w系数，也没有额外的RU*v或SU*v项。启停时也约束above-min部分变化。
- 原代码若Pmin随时间变化，会切换到实际出力及SU/SD公式；本例不适用此分支，不能推广至任意输入。

## 启停限额

来自[base/unit.jl:142](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/base/unit.jl#L142)：

- 全部t：q[t]+r[t] <= (Pmax-Pmin)*u[t] - max(0,Pmax-SU)*v[t]。
- t<T：q[t] <= (Pmax-Pmin)*u[t] - max(0,Pmax-SD)*w[t+1]。
- 如果P0>SD则w[1]<=0。
- 本例所有Pmax和P0远低于缺省SU=SD=1e6，max项为0且初始禁止停机条件不触发。因此这些专用限额可由普通q上界覆盖；不能擅自改为SU=SD=Pmin。

## 最小开停时间、初始义务及终末

[base/unit.jl:228](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/base/unit.jl#L228)：

- 每t：sum(v[i], i=max(1,t-UT+1)..t)<=u[t]；sum(w[i], i=max(1,t-DT+1)..t)<=1-u[t]。
- 初始已在线L>0时，前max(0,UT-L)小时禁止停机（截到T）。初始已停机L<0时，前max(0,DT+L)小时禁止启动（截到T）。
- 窗口只检查至T，不延长到T以后、不强制末态与初态相同、不禁止靠近日末的启动/停机。采用截断终末义务，不添加循环边界。

## 削负荷及供需平衡

[read.jl:186](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/instance/read.jl#L186)默认`Power balance penalty ($/MW)=1000`。

[base/bus.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/base/bus.jl)定义0<=s[t]<=D[t]，净注入为发电-D+s，目标加1000*s。[base/system.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/base/system.jl)令全系统净注入之和0。本例单节点因此sum(P[g,t])+s[t]=D[t]。没有任意方向的平衡松弛或过剩弃电变量。

## 零备用为何可固定为0

read.jl中备用缺额罚价默认-1；base/unit.jl将负罚价类别的shortfall变量上界设0。[base/system.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/base/system.jl)规定sum(r)+shortfall>=requirement。本例所有requirement=0，因此r=0满足备用需求。

原备用变量非负，仅正向占用发电余量及爬坡余量，未带奖励费用。把任意可行解的r减少为0保持u/q/削负荷不变：备用需求仍满足、出力/爬坡约束只会放松、目标不变。所以固定r=0不排除任何原始u/P/削负荷可行投影，也不改变最优目标。此简化仅适用于当前零备用需求实例。

## 验证边界

本文件只核查上述源公式并说明本次计算选择，不保证所有UC.jl其它模块或格式均已移植。两个求解器必须使用完全相同矩阵、变量边界、费用和上述规则；独立验解需重算above-min爬坡、初始剩余义务、截断最小开停、分段生产费用、启动费、削负荷罚费及供需平衡。

## 本例模型实现只读复核

2026-11-05实际读取Lead生成的uc_model.py，核对build_model的全部约束族。当前本例的above-min爬坡、首时段仅初始在线、初始剩余锁定、截断终末最小开停、单档启动费用、凸分段成本epigraph及1000削负荷均与本文所列计算profile一致。原输入无显式SU/SD、Must run、Commitment status或不同Power balance penalty，且Pmax远低于1e6，因此简化成立。未发现本例公式阻塞缺陷。

防误用建议已发Lead：对其他输入若出现上述扩展字段，应拒绝或另作处理，不能静默忽略后仍称源语义一致。此只读实现复核不代替实际求解、矩阵一致性核对或独立调度验解。
