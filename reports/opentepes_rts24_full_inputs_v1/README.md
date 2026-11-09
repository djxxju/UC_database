# openTEPES RTS24 全时域输入校验

固定版本 `5c0187063874cca4bc7af8ff97b19c6c316dd7a5`。对本地 44 份 CSV 逐一复算原字节 SHA256、Git blob SHA1 与字节数，并核对 LICENSE。全部匹配来源清单。校验覆盖 8,736 个原始小时，原始文件保持原值。

| 层次 | 实测结果 |
| --- | --- |
| 结构与关联 | 44 份 CSV 行宽及表头检查通过。节点、分区、区域、大区层级为 24、7、2、1。33 条机组记录与机组字典对应。38 条支路主键唯一、端点及电路引用有效、无自环，网络全体节点可从参考节点 `N_113` 到达。4 对并联支路分别保留。 |
| 时序与数值 | 17 张时序表均与 Duration 的 8,736 个主键按序一致，字段列与原节点、区域或机组字典匹配。确认 305,760 个有限数值、8,736 个阶段标签、3,424,512 个原始空格。两区上下备用均为原表显式零。 |
| 时间转换 | 按源程序两小时分组得到 4,368 个有效时段，覆盖相同 8,736 小时。24 节点负荷逐节点及 6 列储能流入逐机组的全时域积分均保持一致。总负荷 15,297,074.71374 MWh，六列流入总计 2,015,791.86247344 MWh。 |
| 参数与必要条件 | 出力上下限、储能库存与效率、有效年、支路电抗、容量及角度区间检查通过。33 条记录的原名牌有功容量合计 3,405 MW，经固定版 EFOR 规则换算为 3,196.37 MW。原始小时峰荷为 2,850 MW，模型时段峰荷为 2,835.75 MW，零备用口径下两种时域的系统总容量检查均无缺口。该检查只比较总量。 |

## 模型规则与待核项

- 机组爬坡和最小开停时长的原始字段均为空。固定版读取器在模型内部对这些数值采用默认零，约束是否生成还取决于参数有效性。动态出力、充放电和库存上限或下限回退到对应静态值。原空字段与显式零分别计数。[读取默认值](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_InputData.py#L196-L211) · [动态限值回退](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_DataConfiguration.py#L581-L614)
- 38 条支路的反向容量原值均为空，固定版回退到对应正向容量。3 条支路的原电压栏为空，保留原值。六条 Hydro 记录进入储能口径，库存上下界与初值分别为 0.001、0.5、0.25 GWh，效率均为 0.7。固定版对适用的既有储能在阶段末固定初始库存。调相机 `SC_SC001` 原有功容量为零，保留其记录及无功字段。[线路读取](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_InputData.py#L646-L666) · [阶段末库存](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_SettingUpVariables.py#L763-L766)
- `Gas_C31`、`Gas_C32`、`Gas_C33` 的原 `Technology=Coal`。每条记录的水电、制氢和产热转换系数同时为正，三条记录对应原值分别为 0.05、0.18、0.10。固定源码的 `h` 要求制氢和产热系数都为零，`es` 要求水电系数为零。三条记录均落在 `eh` 之外，按输入和源码推导属于普通热机的启停转移规则范围。作者填写意图和实际生成的约束清单标为 `UNVERIFIED`，后续用固定版构建核对。[参数读取](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_InputData.py#L579-L581) · [资源筛选](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_DataConfiguration.py#L139-L143) · [启停转移](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_ModelFormulationElectricity.py#L623-L630)

本次为全原始时域的输入校验及固定源码语义审查。模型构建、COPT 兼容性、调度可行性和求解验解分别记录为待做。[机器校验报告](data_validation.json) · [时间映射证据](../../docs/profiles/opentepes-rts24-source-input-audit/1.0.0/README.md)

## 语义测试

五项测试在内存副本中分别注入未知支路端点、机组最小出力大于最大值、末小时键不匹配、末小时负荷为负及非储能机组流入。五项均由对应校验规则检出。[复跑命令](../../cases/opentepes_rts24_full_inputs_v1/README.md#审计复跑)
