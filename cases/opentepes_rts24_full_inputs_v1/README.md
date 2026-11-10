# openTEPES RTS24 全时域输入审计 v1

固定版 openTEPES `5c0187063874cca4bc7af8ff97b19c6c316dd7a5` 的 RTS24 原输入有 24 个节点、38 条支路、33 条机组记录、一个 period、一个场景和一个阶段。17 张时序表覆盖全部 8,736 个原始小时。按固定版时间转换规则复算得到 4,368 个两小时有效时段。静态总容量检查通过，模型构建、COPT 适配、求解和独立验解均为 `not_run`。[审计报告](../../reports/opentepes_rts24_full_inputs_v1/README.md) · [机器报告](../../reports/opentepes_rts24_full_inputs_v1/data_validation.json) · [待核事项](issues.json)

## 恢复原件

正式包通过来源引用使用原始 CSV。任选以下途径恢复 44 份文件，保留文件名与原字节，并取得固定版仓库根 `LICENSE`。

1. 从固定版 RTS24 目录取得原表。逐文件下载地址、原始 SHA256、Git blob SHA1 与字节数列于 `provenance.json`。[固定版 RTS24](https://github.com/IIT-EnergySystemModels/openTEPES/tree/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/openTEPES/cases/RTS24) · [原件清单](provenance.json)
2. 从原始库第 08 批 Release 下载 `Comillas-openTEPES-5c018706.zip`。按 `provenance.json` 核对 ZIP SHA256，解压后使用其中仓库根的 `openTEPES/cases/RTS24` 与 `LICENSE`。本次重新确认了附件元数据，逐文件审计对本地固定版原件执行。[原始库整包](https://github.com/djxxju/UC_datas_codex/releases/download/official-data-2026-10-18-batch08/Comillas-openTEPES-5c018706.zip)

## 审计复跑

从正式库根目录用 Python 3.10 或更新版本运行，依赖为 Python 标准库。把命令中的路径换成恢复的原始文件路径。`--output` 需要新的文件名，也可省略并输出到标准输出。

```text
python -B scripts/opentepes_rts24/audit_rts24.py --source-dir path/to/RTS24 --license-file path/to/LICENSE --output rts24_audit_rerun.json
python -B scripts/opentepes_rts24/test_audit_rts24.py --source-dir path/to/RTS24 --license-file path/to/LICENSE
```

[时间和模型规则](../../docs/profiles/opentepes-rts24-source-input-audit/1.0.0/README.md) · [逐例校验和](../../reports/opentepes_rts24_full_inputs_v1/checksums.sha256)

## 来源与许可

openTEPES 由 Universidad Pontificia Comillas 的 Instituto de Investigación Tecnológica（IIT）开发。上游项目建议引用 Andrés Ramos、Erik Quispe、Sara Lumbreras 在 *SoftwareX* 18（2022）发表的 openTEPES 软件论文。[论文 DOI](https://doi.org/10.1016/j.softx.2022.101070) · [固定版引用说明](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/README.md)

固定版仓库根附 GNU Affero General Public License version 3 文本，RTS24 目录清单中无单独许可文件。此处保留原仓库许可文本和来源引用，原始 CSV 由上述入口恢复。[固定版根许可](https://github.com/IIT-EnergySystemModels/openTEPES/blob/5c0187063874cca4bc7af8ff97b19c6c316dd7a5/LICENSE) · [许可原文副本](LICENSE.txt)
