# UC.jl OR-LIB原生输入保留 profile 1.0.0

适用本例10_0_1_w，10机组、单节点、零备用需求、24个一小时时段。原JSON Version=0.3，原字节及LICENSE/SOURCE保留。费用为对应出力的总生产费用，启机费在实际启动时另计。

| 原字段 | 含义与单位 |
|---|---|
| Parameters.Time (h) | 日时域长度，本例24；负荷和备用各24值，对应1小时时段 |
| Parameters.Version | 原文件格式版本0.3；不与下载目录0.4混同 |
| Generators对象键、Bus | 机组标识和节点外键，保持原标识 |
| Production cost curve (MW)/($) | 出力及对应生产费用折点；相邻点分段线性，首末出力为在线上下限；本例时段1小时 |
| Initial status (h) | 正数为已连续开机小时，负数为已连续停机小时 |
| Initial power (MW) | 日时域开始前的出力 |
| Minimum uptime/downtime (h) | 最小连续开/停机时间 |
| Ramp up/down limit (MW) | 相邻时段出力变化上限；本例1小时步长；启停过渡及首时段具体应用待核查 |
| Startup costs ($) / Startup delays (h) | 按先前停机时长阈值对应的启动一次费用；后者不是启动过程耗时 |
| Reserve eligibility | 可参与的备用类别标识 |
| Buses.Load (MW) | 按源数组顺序排列的逐小时负荷 |
| Reserves.Type/Amount (MW) | 备用类别及逐时需求，零值按原值保留 |

2026-11-06：本项目执行采用的初始剩余开停时长、非循环末端截断、above-min爬坡、启停限额默认1e6 MW、默认负荷削减罚价1000/MWh已核对，详见[精确模型规则](../../../../scripts/orlib10/MODEL.md)与[核对依据](../../../../scripts/orlib10/SOURCES.md)。这些源默认规则不回写原件。

两求解器实际运行与独立验解均已完成，但结果含0.243366 MWh削负荷，不能称严格全需求可行。见[结果说明](../../../../results/ucjl_orlib_10_0_1_w_native_v1/README.md)。本项目没有执行完整UC.jl软件或复现作者基准结果，原UC.jl/CPLEX读取兼容性仍UNVERIFIED。

Schema及静态检查仅说明其所列结构/数值范围；结构检查、模型执行、验解和来源真实性分别记录，不相互替代。没有线路不表示遗漏网络，本例即单节点实例；不增加RPG循环边界或未定义的停机费。
