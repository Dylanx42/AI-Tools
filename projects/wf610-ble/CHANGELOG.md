# Changelog

## 1.2.0

- 原生 macOS 菜单栏应用：显示连接状态、连接时间和已连接时长。
- 按已知 BLE 地址主动连接 Feasycom FSC-BT826B / WF610BLE。
- GATT 使用实测 FFF0/FFF1/FFF2，FFF3 仅作为模组状态。
- BLE 桥接与 SecureCRT 会话解耦，PTY 固定为 `/tmp/ttyWF610BLE`。
- 修正状态文件带时间戳时被误判为未连接的问题。
