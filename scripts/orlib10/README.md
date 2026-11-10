# OR-LIB 10机组双求解器代码

输入为 `cases/ucjl_orlib_10_0_1_w_native_v1/input.json`。支持本例单节点、零备用需求、单档启动费用、凸分段成本和固定初始状态；模型规则见[MODEL.md](MODEL.md)。保留源读取器默认允许削负荷及1000/MWh罚价，不能把验解通过理解为全部需求满足。

在仓库根目录执行（Python与相应求解器许可须可用）：

```text
python -m pip install -r requirements-orlib10.txt
python scripts/orlib10/solve_compare.py --solver both --output reproduce_orlib10
```

只运行一个时将both改为gurobi或copt。输出目录须不存在，避免覆盖。`--input`可指定同格式输入路径；默认每个求解器600秒、1线程、相对gap1e-8。完整日志、LP/MPS、候选、调度及验解写入所指定目录。输入数据不会改写。

`uc_model.py`建立共同系数模型；`solve_compare.py`分别调用两后端；`check_solution.py`独立重算约束和费用。

本次实际结果见[结果摘要](../../results/ucjl_orlib_10_0_1_w_native_v1/README.md)。两者容差内最优且验解通过，总目标1929392.436364，含0.243366 MWh削负荷。不是作者结果复现或求解器性能排名。

可选运行现有测试：`python -m unittest discover -s scripts/orlib10 -p "test_*.py"`。测试含小例双后端，因此也需要相应许可。求解代码为本项目编写，SOURCES.md仅记录已经核对的上游规则依据。
