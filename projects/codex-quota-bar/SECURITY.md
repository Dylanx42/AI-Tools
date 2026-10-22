# Security

## Supported version

当前维护版本：0.6.x；接入基线 OpenCodex 2.90.0。

## Security boundary

- 仅启动本机 OpenCodex CLI，使用固定参数 `account list openai --quota --refresh --json`；不通过 shell 拼接或执行账户输入。
- 管理接口认证、上游登录凭据和刷新由 OpenCodex 负责；不直接读取或复制凭据。
- 账户选择只更新额度栏偏好，不调用账户切换或路由修改接口。
- JSON 字段按类型校验，缺失额度不解释为 0% 已用；输出有大小上限、进程有读取期限；原始 stderr 不进入界面或日志。
- 趋势文件名采用账户 ID 的 SHA-256，避免路径穿越；CSV 不保存邮箱、原始 ID、令牌或完整响应。文件创建权限为 `0600`、目录为 `0700`。
- 取消、超时和退出只终止应用自行启动的 CLI 查询进程，不停止 OpenCodex 服务。
- Finder 启动时补全 CLI 运行环境 PATH；这些可执行路径和已安装 OpenCodex 是本机用户信任边界的一部分。
- 构建产物使用 ad-hoc 签名；公开分发应使用 Apple Developer ID 签名并公证。

## Reporting

请通过仓库的私密安全报告功能提交潜在漏洞，不要在公开 Issue 中粘贴 Token、完整日志、账户 ID 或原始额度响应。
