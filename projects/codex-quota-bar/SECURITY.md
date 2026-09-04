# Security

## Supported version

当前维护版本：0.3.x。

## Security boundary

- 应用只启动本机可执行的 Codex CLI，并使用官方 app-server JSON-RPC 接口。
- 不直接读取或复制登录凭据。
- 本地趋势文件只记录额度时间与百分比，创建时权限为仅当前用户可读写。
- 每次额度读取完成后终止应用自行启动的 app-server 子进程。
- 构建产物使用 ad-hoc 签名；公开分发者应自行使用 Apple Developer ID 签名并公证。

## Reporting

请通过仓库的私密安全报告功能提交潜在漏洞，不要在公开 Issue 中粘贴 Token、完整日志、账户 ID 或原始额度响应。
