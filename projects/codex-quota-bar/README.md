# Codex 额度栏

原生 macOS 菜单栏额度查看器。**0.6.0 / Build 18** 起统一通过本机 OpenCodex 读取已登录的 ChatGPT/Codex 账户，可在菜单里手动选择监控账户。

## 日常使用

1. 先启动 OpenCodex，在其中完成账户登录；确认 `ocx status` 正常。
2. 打开额度栏，点击顶部的「监控账户」子菜单，选择要查看的账户。勾选项是监控对象，「OpenCodex 当前」标记的是本次查询报告的选中账户，两者可以不同。
3. 首次默认选中 OpenCodex 报告的当前账户；没有当前项时选列表首项。之后记住明确的账户 ID，不跟随 OpenCodex 自动换号。已选账户被移除时提示重新选择，不静默追踪另一个账户。
4. 选择只改变额度栏展示和本地趋势文件，不调用账户切换、优先级、暂停或路由设置接口。读取中暂时禁用选择，避免请求返回时混淆账户。

菜单栏固定按「短窗口 · 长窗口」显示剩余百分比。通常是 5 小时 / 7 天；仅返回月窗口时，长窗口显示 30 天。未返回的窗口显示 `—` /「暂无数据」，不视作剩余 100%。接口已用百分比转换成剩余比例后显示。

保留双窗口卡片、精确重置时间、最近 7 天的原生趋势图、横向最近真实采样点悬停提示和重置标记。只在额度百分比或窗口变化时追加趋势。CLI 目前不投影 Credits、重置券详情或其他自定义窗口，这些不会被推算或补成零。

## 数据来源和刷新

每次读取启动一个本机 CLI 子进程，执行已在 OpenCodex **2.90.0** 上验证过的命令：

```sh
ocx account list openai --quota --refresh --json
```

OpenCodex CLI 负责定位正在运行的服务、管理接口认证、账户凭据和上游额度刷新。额度栏只解析账户 ID、展示名称、套餐、选中状态、额度窗口和刷新状态，不再启动官方 `codex app-server`。应用本身不调用模型；使用额度查询命令，不使用账户验证或推理命令。

该命令请求刷新整个 Codex 账户列表，额度栏只显示、记录选中的账户。读取也会更新 OpenCodex 自身的额度缓存，供其现有路由规则使用。

- 额度变化或剩余 ≤20%：30 秒；连续 1～4 次稳定：60 秒；持续稳定：2 分钟。
- macOS 低电量模式：5 分钟；失败后按 1、2、5 分钟退避。
- Mac 唤醒后立即读取；打开菜单且距上次成功读取超过 20 秒时也读取；可手动「立即刷新」。
- CLI 总读取上限 60 秒、输出上限 2 MiB。取消或超时仅结束额度栏启动的查询进程，不停止 OpenCodex 服务。
- 界面时间是 **CLI 读取时间**，不是上游观察时间。明确失败、超时、需重新登录、暂停或没有额度时提示，缓存不记作新趋势点。部分窗口缺失时仍展示其他已知窗口。

## 要求

- macOS 13 Ventura 或更高版本，以及 Command Line Tools。
- 本机 OpenCodex 已安装、服务正在运行、至少登录一个 ChatGPT/Codex 账户；接入基线为 2.90.0。
- `ocx account list openai --quota --refresh --json` 可正常执行。
- 自动查找 `/opt/homebrew/bin`、`/usr/local/bin`、`~/.local/bin`、`~/.bun/bin` 和常见版本管理器目录，也支持进程继承的绝对 PATH 目录。启动 CLI 时补全 Node/Bun 常用 PATH，支持从 Finder 启动。

## 构建和安装更新

在本项目目录运行：

```sh
plutil -lint Info.plist
./test.sh
./build.sh
codesign --verify --deep --strict --verbose=2 "dist/Codex 额度栏.app"
```

先从菜单退出正在运行的旧额度栏，再覆盖安装：

```sh
ditto "dist/Codex 额度栏.app" "/Applications/Codex 额度栏.app"
open -a "/Applications/Codex 额度栏.app"
```

构建使用本机 ad-hoc 签名，无第三方构建依赖。CI 在 macOS 构建和验证；CI 产物不替代 Mac 本地安装与交互验收。当前没有自动更新器或开机自启功能。

## 本地记录与隐私

- 监控账户 ID 保存在应用的 `NSUserDefaults` 偏好中。
- 新趋势在 `~/Library/Application Support/CodexQuotaBar/opencodex-accounts/account-<账户ID的SHA256>.csv`，按账户 ID 隔离，不写邮箱或完整响应。`__main__` 对应主账户槽位；替换该槽位登录身份前，应备份并移出对应旧 CSV，避免不同身份并入同一槽位历史。
- 原有 `~/Library/Application Support/CodexQuotaBar/quota-history.csv` 完整保留，不自动迁入任何账户，因为旧版没有记录账户身份。
- 登录、管理令牌和账户凭据交给 OpenCodex CLI；额度栏不解析 `auth.json`、OpenCodex 凭据文件或 Keychain，不输出原始 CLI stderr，也不保存原始 JSON 响应。

详见 [PRIVACY.md](PRIVACY.md)、[SECURITY.md](SECURITY.md) 和 [接入决策](docs/decisions/0001-opencodex.md)。

## 验证与维护交接（2026-10-23）

触发：用户在 OpenCodex 使用多账户，希望独立选择额度栏的监控对象。本机提供的 2.90.0 CLI 输出证明账户列表、选中 ID、短/周窗口可读取；这些查询发生在代码改动之前，不代表新版 App 已安装或验收。

本次开发在 Linux 云端完成；macOS 编译、签名和离线回归由项目 CI 检查。测试使用合成数据和模拟 CLI，不连接真实账户。验证结论随本次 PR / [CHANGELOG.md](CHANGELOG.md) 更新。

Mac 本地待验收：

- Finder 启动后可找到 `ocx`，读取账户列表和当前额度；确认版本 0.6.0 / Build 18。
- 在「监控账户」选择 Plus / Pro，勾选和双窗口数据对应选择；重启 App 后记住选择，OpenCodex 实际选中账户未被额度栏切换。
- Pro 未返回 5 小时窗口时显示暂无数据；两账户曲线相互独立且旧 CSV 保留。
- 停止服务、需重新登录或上游失败时提示可读，恢复服务后可刷新；深浅外观、悬停和重置标记正常。

源码发布不等于本地 App 已更新。后续维护从最新 `origin/main`、本 README 和变更记录开始。
