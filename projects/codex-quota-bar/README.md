# Codex 额度栏

轻量、原生的 macOS 菜单栏 Codex 额度查看器。它直接通过本机官方 `codex app-server` 读取 ChatGPT Codex 的额度窗口，不解析登录文件，也不需要浏览器 Cookie。

## 功能

- 菜单栏直接显示 5 小时和 7 天窗口的剩余百分比。
- 点击后查看已用比例、精确重置时间、套餐、Credits 和可用重置券。
- 智能刷新：额度变化或接近阈值时每 30 秒，短期稳定时每 60 秒，持续稳定后每 2 分钟。
- 低电量模式降至 5 分钟；连续失败时按 1、2、5 分钟退避。
- Mac 唤醒后立即刷新；打开菜单且数据超过 20 秒时也会立即刷新。
- 无 Dock 图标、无第三方运行时依赖。

## 工作方式

应用启动本机 `codex app-server`，完成 JSON-RPC 初始化后调用：

```json
{"method":"account/rateLimits/read","id":1}
```

读取成功后立即结束该辅助进程。应用不会调用模型，不消耗对话 Token。

## 隐私

- 不读取浏览器 Cookie。
- 不解析 `~/.codex/auth.json`。
- 不保存或上传访问令牌、完整额度响应、提示词或聊天记录。
- 只使用 `account/rateLimits/read` 返回的额度窗口、套餐、Credits 和重置券数量。

完整边界见 [PRIVACY.md](PRIVACY.md)。

## 要求

- macOS 13 Ventura 或更高版本。
- 已安装并登录 Codex CLI。
- 默认查找 Homebrew、`~/.local/bin` 和 Codex.app 常见安装位置。

## 构建

不需要 Xcode 工程或第三方依赖，安装 Command Line Tools 后执行：

```sh
chmod +x build.sh
./build.sh
```

产物：`dist/Codex 额度栏.app`

构建脚本使用本机 ad-hoc 签名，适合本机自用。对外分发需要 Apple Developer ID 签名与公证。

## 安装

```sh
ditto "dist/Codex 额度栏.app" "/Applications/Codex 额度栏.app"
open -a "/Applications/Codex 额度栏.app"
```

## 验证

```sh
plutil -lint Info.plist
codesign --verify --deep --strict --verbose=2 "dist/Codex 额度栏.app"
```

## 项目结构

```text
.
├── Sources/main.m
├── Info.plist
├── build.sh
├── README.md
├── PRIVACY.md
├── SECURITY.md
└── CHANGELOG.md
```

## 当前限制

- 当前仅显示一个 Codex 额度桶的主/次窗口。
- 不包含自动更新器、开机自启或多 Provider 支持。
- Bundle 为本机构建；仓库本身不提供 Apple 公证产物。
