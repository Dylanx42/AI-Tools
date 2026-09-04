# Privacy

Codex 额度栏是本地优先的菜单栏工具。

## 读取的数据

应用通过本机 `codex app-server` 调用 `account/rateLimits/read`，只使用：

- 额度窗口的已用百分比、窗口长度和重置时间；
- ChatGPT 套餐类型；
- Credits 余额（服务端提供时）；
- 可用重置券数量（服务端提供时）。

## 不读取的数据

- 浏览器 Cookie、历史记录或本地存储；
- `~/.codex/auth.json` 的原始 Token；
- Codex 对话、提示词、项目文件或会话日志；
- Keychain 内容。

## 存储与传输

应用不会持久化完整额度响应。为了展示本机使用趋势，它只在额度百分比或窗口发生变化时，将以下字段追加到本地 CSV：

- 记录时间；
- 主/次额度窗口的已用百分比、剩余百分比和窗口长度；
- 主/次额度窗口的重置时间。

文件路径为 `~/Library/Application Support/CodexQuotaBar/quota-history.csv`，仅当前用户可读写。删除该文件即可清空趋势历史，应用下次启动时会重新建立记录。

应用不上传遥测，也不连接自有服务器。所有网络认证由用户已安装并登录的 Codex CLI 处理。
