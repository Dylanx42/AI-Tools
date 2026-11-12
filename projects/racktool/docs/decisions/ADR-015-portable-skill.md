# ADR-015: 带 Core 的版本化独立 Skill 包与本地验收

- Status: Accepted
- Date: 2026-10-14
- Extends: ADR-014

## Context

用户希望在 Codex、WorkBuddy 和 TRAE 测试 Skill，不再为使用工具同步整个 monorepo。
先前技能 ZIP 只有说明和参考文件，源码目录安装器生成 runtime.json 指向仓库，不包含 Core。
仅能被 Agent 读到技能说明不能证明 Core 已安装或实际调用正确。

## Decision

- 提供 ZIP 根目录直接包含 SKILL.md 的独立交付包，包含同一份 RackCore/CLI/Profile，
  安装器和 runner 只定位和调用现有 CLI，不复制任何业务逻辑。
- 打包固定版本 openpyxl、et_xmlfile、PyYAML 的纯 Python 源码、元数据和许可证，不带
  PyYAML 原生扩展、GUI、解释器、私有样本或 SQLite；用户仍需 Python 3.11+ 和 Agent 脚本能力。
- runner 优先使用包内 Core/vendor，禁用 openpyxl 可选宿主加速器，避免旧仓库/平台二进制依赖。
  Core 离线可用不代表 Agent 对话离线或业务内容不会进入所用 Agent 的模型上下文。
- 构建器白名单选择有效载荷，包记录独立版本、Git 提交、dirty 状态、依赖版本和文件 SHA256。
  正式交付只使用干净提交；包内清单不包含自身，不能当作数字签名。
- 安装不覆盖已有同名目录；旧安装先移出扫描目录保存，新版查实际来源；业务状态置于技能目录外。
  开发源码安装保留，与独立包安装在文档中明确区分。
- 本地验收分为独立运行、各 Agent 自然语言调用、Excel/WPS 人工输出核对三层。
  云端自动化只能验证第一层和 Core 行为，后两层必须记录实际平台证据。
- 发布源码/文档走 GitHub PR；构建 ZIP 不入 Git。初轮会话附件交付后按下述更新转为正式 Release。

## Validation / Limits

脱离仓库解压到带空格路径，子进程 -S 禁用 site-packages，验证包内导入、纯 Python YAML、
空柜生成、新建项目编辑/冲突拒绝、文件完整性和重复安装保留；真实私有图在独立包中复跑。
Agent 的目录发现/ZIP 导入/脚本执行和桌面 Excel/WPS 外观仍需本地人工验收。
本 ADR 初次验收时（2026-10-14）绑定设备高度调整和跨 Sheet 移动尚未支持；随后已由
[ADR-016](ADR-016-skill-workflows-and-table-roundtrip.md) 扩展为同一项目、同一工作簿内的安全编辑。
打包本身不改变 Core 能力，具体支持范围与对象保护由对应发布提交决定。

## 2026-10-15 更新：安装与开发者构建分开

用户本机 Agent 因“无发布包则自行构建”的提示词而下载源码并构建，违背成品安装预期。
增加专用 GitHub Actions 发布流程：PR 阶段只读权限构建/核验，只有 RackTool 专用版本标签
才在独立作业申请 contents:write 创建 Release，不将其标为 monorepo 全局 latest。
完整 ZIP 和 SHA256 由 GitHub 构建器发布，普通安装只下载/校验/安装。无法下载时报告阻塞，
不默认回退源码构建。开发者构建只用于维护和发布；系统 CI 仍不代表 Agent 软件兼容通过。
