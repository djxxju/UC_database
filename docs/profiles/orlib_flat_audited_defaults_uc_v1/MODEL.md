# OR-LIB 单节点 24 小时 UC 模型

计算 profile 为 `orlib_flat_audited_defaults_uc_v1`。本例采用归档的 UC.jl 0.3 JSON，并以 UC.jl 固定提交 `e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a` 中的相应默认规则为依据。默认规则只进入本项目计算模型，原 JSON 不增列。

- 时间从 1 到 24，每时段一小时。初始开机与否由 `Initial status (h)` 的正负决定，绝对值给出已持续时间。前序状态与初始出力独立保留。
- 开机、启动、停机状态为二元量，状态差等于启动减停机，同小时最多发生一种切换。按剩余开停义务锁定前若干时段，按原最小时间检查每一小时的启动和停机窗口。窗口截至第 24 小时。
- 每台每小时的凸成本曲线由非负权重表示，权重之和等于开机状态。实际出力和生产费用分别等于原 MW 折点和原费用折点的加权和。最小化目标保证在给定出力下取凸分段曲线费用。单档启动费乘启动状态。
- 对高于最小出力的部分计算爬坡，记为实际出力减开机状态乘最小出力。首小时的爬坡检查只对初始在线机组使用。缺省启动和停机出力限额均为 1,000,000 MW，高于本例所有适用出力，相关专用限额冗余。
- 每小时总出力加削负荷等于负荷。削减可在零和该小时负荷之间取值，默认罚价为每 MWh 1,000。目标为生产费、启动费及削负荷罚费之和。
- 原输入每小时旋转备用需求均为零。备用取零满足需求，而且减少非负备用只会放松出力和爬坡约束，因此可以固定为零。本 profile 的计算实现拒绝非零备用或未支持的显式覆盖值。
- 本例只有一个母线。线路、潮流和网络安全约束不适用。当前实现范围为平面数组、凸成本、单档启动和零备用的所选 profile。

依据为 UC.jl 固定代码的[输入读取](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/instance/read.jl)、[爬坡约束](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/MorLatRam2013/ramp.jl)、[机组约束](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/base/unit.jl)和[母线平衡](https://github.com/ANL-CEEESA/UnitCommitment.jl/blob/e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a/src/model/formulations/base/bus.jl)。本次实际运行使用 COPT 和项目适配器。独立检查器从原参数和候选值重算约束及目标，作者结果对照和 Julia 直接导入均为未验证。
