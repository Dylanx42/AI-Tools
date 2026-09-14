# Privacy

- 应用只在本机通过 CoreBluetooth/bleak 连接已配对的 WF610BLE。
- 不上传蓝牙地址、串口内容、SecureCRT 日志或设备配置。
- 状态文件只写在 `/tmp/wf610-ble-bridge.state`，包含连接状态和时间戳。
- 桥接日志只写在 `/tmp/wf610-ble-bridge.log` 与 `/tmp/wf610-ble-menubar.log`。
- 不读取浏览器、Keychain 或 SecureCRT 密码。
