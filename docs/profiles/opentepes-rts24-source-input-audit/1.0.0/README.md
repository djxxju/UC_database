# openTEPES RTS24 原始输入审计 profile 1.0.0

本次核查固定提交 `5c0187063874cca4bc7af8ff97b19c6c316dd7a5` 的输入和原程序。源包只有 period 2030、场景 `sc01` 和阶段 `st1`，权重和概率均为 1。17 张原时序表使用同一组 8,736 个键。原始全时域仍为整理和校验范围。

## 时间分辨率

- 源程序先将原 `Duration` 乘以 `TimeStep`。本包的 `Duration` 为 1，`TimeStep` 为 2。源程序对适用的动态参数做两行滚动平均，并将每组非末尾时标的 duration 置零；有效时标对应原行序号 2、4、…、8,736。[固定版输入读取](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_InputData.py#L394-L536)
- 固定版配置仅保留正权重、正概率、非零 duration 的时段，并将时段对应到阶段。Lead 用原 Duration、Demand 和 Decimal 在内存逐小时验证，原时标连续，全部 8,736 行可配成 4,368 组。每节点以两小时均值乘两小时所得全时域电量均与原逐小时总量相等。模型有效标签从 2030-01-01 01:00:00+01:00 到 2030-12-30 23:00:00+01:00。全部原记录参与，模型步长体现作者的变换规则。[固定版时段配置](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_DataConfiguration.py#L263-L280)
- 机组最小开停等以有效 duration 换算；阶段首段有源程序构造的初始机组、线路及库存设置，启停约束从该初始状态衔接，后续连接上一有效时段。适用的既有储能终点有库存约束。适用对象及具体数值留待下一阶段按原表核对。[时长换算](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_DataConfiguration.py#L617-L620) · [初始设置](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_SettingUpVariables.py#L725-L766) · [启停关系](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_ModelFormulationElectricity.py#L623-L630)

独立复核使用 pandas 3.1.0 重做相邻小时均值，输入及模型形状分别为 `8,736×24` 与 `4,368×24`，逐节点积分最大差为 `1.63e-9 MWh`。固定版最小开停窗口在阶段起点按时段序号和换算后最小时间处理，首时段爬坡使用源程序构造的初始出力和启停状态。[最小开停窗口](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_ModelFormulationElectricity.py#L904-L917) · [首段爬坡](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/openTEPES_ModelFormulationElectricity.py#L770-L795)

## 原时序表基础结构

Lead 逐行检查 17 张时序表的列数和表头唯一性。联合键之外有 305,760 个可解析的有限数值、8,736 个合法阶段标签和 3,424,512 个原始空单元格。空值集中在出入流和动态约束、成本等表，后续逐字段按固定版读取和模型逻辑解释适用性。此次按原样计数。

## 适用范围

此 profile 审计固定版原生 CSV，字段名、原顺序、原空值与单位沿用上游记录。逐文件身份和已执行检查在报告中记录。下一阶段需构建固定版模型以核实实际变量、约束及阶段边界，并单独验证 COPT 适配。[算例与复跑命令](../../../../cases/opentepes_rts24_full_inputs_v1/README.md) · [输入审计报告](../../../../reports/opentepes_rts24_full_inputs_v1/README.md)
