# OR-LIB 20_0_1_w 参考计算结果

COPT 8.0.7 单线程运行 120 秒后达到时限，保留了通过独立验解的整数可行候选。最终目标 2,952,707.69439072，最好界 2,950,140.69629994，相对 gap 0.0869371%，本次未证明最优。

重算生产费用为 2,949,936.7807047213，启动费用为 2,770.913686。逐小时削负荷在容差内为零，原始浮点合计为 −9.094947017729282e−13 MWh。验解最大残差为 3.637978807091713e−12，约束容差 1e−5，目标绝对容差 1e−4。

- `reference_results.csv` 为一行汇总，含原始削减浮点量和容差内值。
- `run_manifest.json` 为实际运行的输入、代码和模型哈希，记录 3,864 变量、1,440 二元变量与 3,366 行。
- `solve_metadata.json` 为求解器原始状态码、运行参数及数值。状态码 8，原始日志显示 `stopped (time limit reached)`。
- `verification.json` 为独立于建模系数的检查器输出。

模型与依据见[模型说明](../../docs/profiles/orlib_flat_audited_defaults_uc_v1/MODEL.md)，输入见[算例目录](../../cases/orlib_20_0_1_w/README.md)。使用具有 COPT 许可的环境，在仓库根目录执行：

```powershell
python -B scripts/orlib20/solve_compare.py --input cases/orlib_20_0_1_w/input.json --solver copt --time-limit 120 --gap 0.00001 --output reproduce_orlib20
```

时限结果可能随环境变化，重新运行会生成自己的结果和验解记录。详细原始候选、日志及模型导出留在本地。作者结果对照未执行。
