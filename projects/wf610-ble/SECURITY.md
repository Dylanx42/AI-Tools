# Security

## Supported version

当前维护版本：1.2.x。

## Security boundary

- 菜单栏应用只启动本机 `scripts/wf610-ble-open.sh` / `wf610-ble-stop.sh`。
- BLE 目标默认锁定为本机实测设备 `WF610BLE` / `56864941-4310-3722-B52D-EA59372A16B9`。
- 构建产物使用 ad-hoc 签名，适合本机自用；对外分发需要 Apple Developer ID 签名与公证。
- 不要把 `.venv`、本机 `/Applications/WF610 BLE.app` 或 SecureCRT 会话文件提交进仓库。

## Reporting

请通过仓库的私密安全报告功能提交潜在问题，不要在公开 Issue 中粘贴完整 GATT 抓包或设备配置。
