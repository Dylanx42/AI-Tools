# 2026-10-26：纯改名入口一致性与拒绝证据

## 问题与范围

本地接管发现只改设备文字的 `conversation edit` 被工作簿对象保护拒绝；复现审计进一步确认，
同一源文件和 SQLite 上，专用 `sync rename` 可生成安全改名计划，通用 `sync edit`、对话编辑
和位置表回导却按位置/高度编辑检查无关图表。对话预检还把 Core conflicts 压成一句话，
丢失实体 ID、候选位置和 evidence，无法解释哪个单元格或 OOXML 部件导致拒绝。

本轮由本地 Agent 负责，从 `origin/main` 的 `a35904fb8601b2ac32f3e7b426d8727669615cd8`
建立独立 `fix/racktool-rename-consistency` 工作区；只处理上述入口差异和拒绝信息。
用户明确暂缓真实图和 WPS，本工作区不复制私有样本、不打开 Office、不替换已安装 Skill。

## 修复行为

- RackCore `plan_device_edit` 按实际目标机柜与占用 U 范围识别纯改名，复用已有
  `plan_device_rename`。显式原位置、隐式原位置和倒序 U 端点得到同样的 rename 计划；
  对话、sync edit、位置表整批回导共用这一判断。相同文字保留无操作行为。
- 继续使用原有备份、临时写入、OOXML 保留、写后重载、身份核验和 SQLite 失败回滚链路。
  不取消作用范围内的批注、超链接、数据验证、定义名称等保护；位置/高度变化仍执行原有
  工作簿对象检查，错误说明改为 location/height edits，涵盖同 Sheet 的位置变化。
- 对话 Core 使用 ValueError 子类携带完整 conflicts，CLI 保留原 status/message/退出码 2，
  另输出 code、severity、entity_ids、candidate_refs、evidence 等结构化详情。
  请求校验/token/文件错误不伪造成 Core conflict；首次预检失败不创建计划或密钥。
- 旧签名预览若记录 generic edit，升级后变成 rename，按既有摘要一致性检查拒绝，必须重新预览。
  不绕过 token，不改旧计划。设计澄清见 ADR-016，调用契约见 Skill commands.md。

## 本次验证

2026-10-26，macOS 27.2 / arm64、Python 3.11.9，使用当前工作区 `.venv` 的源码 Core，
已核对 `racktool.__file__` 属于该工作区 `src/racktool/`；未调用已安装 Skill。
新增 `tests/integration/test_rename_consistency.py` 的 19 个合成用例，覆盖：

- 同 Sheet/其他 Sheet 含无关图表时，对话两种参数形式、sync edit 和位置表回导均可改名；
  device/placement/mapping 身份、U、合并、常见样式及备注保持，目标 Sheet 之外所有 OOXML
  部件逐字节一致，包括图表、绘图、关系与 styles。
- 改位、改高、跨 Sheet 继续拒绝；命中批注/链接/验证/定义名称继续拒绝，CLI 完整保留证据，
  源 XLSX 与 SQLite 字节不变。
- 相同文字无写入、数据库持久化故障回滚两文件、旧 edit 预览升级后拒绝并要求重新预览。

修复前运行新增测试得到 **18 failed、1 passed**，分别暴露入口不一致、证据丢失和旧计划行为；
修复后新增 19 项全部通过。与对话、绑定编辑、专用改名和位置表回导既有测试一起跑为
**140 passed、1 warning**，14.13 秒（重叠子集，不与完整测试数量相加）。

完整 `python3 scripts/dev.py check` 为 **PASS**：

| 检查 | 本次结果 |
| --- | --- |
| pytest | 614 passed、5 skipped、1 warning，176.64 秒 |
| pip check / Ruff | PASS |
| strict mypy | PASS，46 个源文件 |
| 源码 CLI help | PASS |

5 项 skip：GUI 模块未安装 PySide6（1）、未带入真实 Golden/私有 Profile（2）、
另一份私有混合方向图未安装（2）。warning 为既有 worksheet 扩展拒绝回归的 openpyxl 提示。

## 留待后续

真实私有 Golden、本地真实 Agent 业务编辑、Excel/WPS 打开保存/外观/打印验收均未在本轮执行。
合成回归证明上述受控情形，不能据此承诺任意图形/嵌入对象兼容。Windows 自动化以本 PR
实际 CI 为准，Windows 桌面人工验收仍待完成。此次只开 PR；主线合并、正式 Release 和本机
固定版 Skill 更新分别按后续授权执行。
