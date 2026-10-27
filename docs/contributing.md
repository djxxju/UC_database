# 新算例入库规则

## 目录和命名

case_id采用`来源_系统_模型或变体_v主版本`，仅用英文小写、数字、下划线；示例为`rpglab_ieee24_native_v1`。编号固定并全库唯一。日期和求解批次写元数据，不拼入正式文件名。数值或模型含义变化时使用新变体/主版本并说明变化。

- cases/<case_id>/：适用profile要求的输入，以及README、来源记录和缺口清单。
- reports/<case_id>/：data_validation.json、checksums.sha256。
- results/<case_id>/：有真实结果时保存reference_results.csv、verification.json和README。
- docs/profiles/<profile_name>/：字段、单位、模型语义，供同profile复用。
- schema/：对应profile的Schema。
- scripts/：按profile支持的共享读取/校验/求解工具。
- templates/case/：新算例说明模板，不是有效数据或已完成算例。
- catalog.json：全库索引；每个case分别记录profile、family、路径、规模、质量和执行状态。

目录树是固定入口，具体算例收到并识别后再建子目录。case_count是索引条目数，system_count按可识别的独立基础系统统计；日样本、参数变体和系统数分别记录，不按文件或负荷行数推算系统数。

## 每次增加算例

1. 固定来源、版本、日期、许可、引用和原文件哈希；原件归档留原始资料库或本地缓存，标准化库保留可恢复来源。
2. 选择或定义profile，确认字段、单位、时间轴、成本、边界、网络和其他模型口径。保留作者原值与模型；有实质变化时单独标记派生模型。
3. 在cases/<case_id>/形成输入、README、provenance和issues；对缺失/不适用/歧义分别标注，不编造数据。
4. 执行实际可做的结构、源值映射、语义和必要条件检查，将报告放reports/<case_id>/。
5. 仅在实际执行后登记求解与独立验解。未运行写not_run，失败/无候选按真实状态记录，不能为了入库删掉异常原件。
6. 有结果时生成results/<case_id>/参考总表和摘要，保留参数、资源、状态、界/gap、容差和工具身份。
7. 更新catalog.json及根README的算例表；验证路径、哈希、样本覆盖和状态一致性。
8. 更新该例checksums.sha256。清单排除全库索引、根README、其他算例及清单自身。共享规范/代码一旦被引用，修改须说明版本和受影响范围。
9. 先查看Git待提交清单，再提交/推送；发布后核对远端文件。完整日志、逐次LP、恢复缓存、完整变量、工作计划/日志不随算例提交。

原件、转换、数据检查、求解、独立验解和发布是不同状态。对新模型不能因复用文件夹或Schema就宣称已完成COPT/Gurobi适配。

## 后续重复提交

仓库首次克隆一次即可。以后在同一个UC_database_git目录，开始修改前先git pull --ff-only取得远端更新；加入新算例及报告/真实结果，更新catalog和根README，检查git diff和git status，再git add、git commit、git push。不要为每个算例重建Git仓库或复制原件缓存进正式目录。
