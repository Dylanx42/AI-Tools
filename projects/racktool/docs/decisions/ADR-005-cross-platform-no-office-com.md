# ADR-005: RackCore 不依赖 Office COM 或 Windows-only 自动化

- Status: Accepted
- Date: 2026-08

## Context

目标用户同时存在 macOS 和 Windows 环境，且项目希望低依赖、易分享。

使用 Excel COM/VBA 会绑定 Windows 和 Office 安装。

## Decision

RackCore 使用跨平台 Python 方式直接处理 `.xlsx`，初期优先 `openpyxl`。

禁止把以下内容作为 V1 核心依赖：

- Excel COM；
- Windows-only Office automation；
- 启动 Excel/WPS GUI 进程完成核心解析。

## Consequences

优点：

- macOS/Windows 共用代码；
- CI 容易；
- 离线；
- 不需要 Office 才能跑自动测试。

代价：

- 对 Shape、宏、某些高级 Office 对象支持有限。
