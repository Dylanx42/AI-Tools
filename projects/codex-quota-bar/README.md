# Codex 额度栏

原生 macOS 菜单栏额度查看器，当前源码 **0.6.3 / Build 21**。自 0.6.0 起统一通过本机 OpenCodex 读取已登录的 ChatGPT/Codex 账户，可在菜单里手动选择监控账户。

## 日常使用

1. 先启动 OpenCodex，在其中完成账户登录；确认 `ocx status` 正常。
2. 打开额度栏，点击顶部的「监控账户」子菜单，选择要查看的账户。勾选项是监控对象，「OpenCodex 当前」标记的是本次查询报告的选中账户，两者可以不同。
3. 首次默认选中 OpenCodex 报告的当前账户；没有当前项时选列表首项。之后记住明确的账户 ID，不跟随 OpenCodex 自动换号。已选账户被移除时提示重新选择，不静默追踪另一个账户。
4. 选择只改变额度栏展示和本地趋势文件，不调用账户切换、优先级、暂停或路由设置接口。读取中暂时禁用选择，避免请求返回时混淆账户。

菜单栏固定按「短窗口 · 长窗口」显示剩余百分比。通常是 5 小时 / 7 天；仅返回月窗口时，长窗口显示 30 天。未返回的窗口显示 `—` /「暂无数据」，不视作剩余 100%。接口已用百分比转换成剩余比例后显示。

保留双窗口卡片、精确重置时间、最近 7 天的原生趋势图、横向最近真实采样点悬停提示和重置标记。只在额度百分比或窗口变化时追加趋势。0.6.1 恢复所选账户的重置券数量、最近到期时间，悬停查看全部已知到期时间；数量确认为零、暂不可用和到期时间缺失分别显示。可用数量优先取 `available_count`；带状态的明细只使用 `available`。OpenCodex 2.90.0 省略明细状态时，只有完整有效列表与可用数量一致才显示这些到期时间；不一致则保留数量、显示到期时间暂无数据，缺少汇总时不靠无状态列表推算数量。账户列表 CLI 未提供的 Credits 余额或其他自定义窗口仍不推算。

## 数据来源和刷新

每次读取启动一个本机 CLI 子进程，执行已在 OpenCodex **2.90.0** 上验证过的命令：

```sh
ocx account list openai --quota --refresh --json
ocx account reset-credits <监控账户ID> --json
```

OpenCodex CLI 负责定位正在运行的服务、管理接口认证、账户凭据和上游额度刷新。额度栏解析账户列表及重置券只读查询响应中的账户 ID、展示名称、套餐、选中状态、额度窗口、刷新状态、重置券数量和到期时间，不再启动官方 `codex app-server`。应用本身不调用模型；使用额度查询命令，不使用账户验证或推理命令。

账户列表命令请求刷新整个 Codex 账户列表，额度栏只显示、记录选中的账户；重置券命令仅查询该监控账户。读取也会更新 OpenCodex 自身的额度缓存，供其现有路由规则使用。

- 额度变化或剩余 ≤20%：30 秒；连续 1～4 次稳定：60 秒；持续稳定：2 分钟。
- macOS 低电量模式：5 分钟；失败后按 1、2、5 分钟退避。
- Mac 唤醒后立即读取；打开菜单且距上次成功读取超过 20 秒时也读取；可手动「立即刷新」。
- 账户列表读取上限 60 秒，独立重置券查询上限 15 秒，输出各限 2 MiB。重置券查询失败只显示“暂不可用”，不阻断额度展示；切换账户立即清空旧券信息，并丢弃旧请求的迟到结果。取消或超时仅结束额度栏启动的查询进程，不停止 OpenCodex 服务。
- 界面时间是 **CLI 读取时间**，不是上游观察时间。本地命令成功且有额度窗口时正常显示；OpenCodex 2.90.0 的池账户可能不返回 `quotaRefresh`，缺失或 `not_reported` 只在底部普通标注“上游状态未提供”，不视作失败或进入失败退避。只有 `quotaRefresh.status=ok` 才将额度视为本次确认的新数据并追加趋势；未知状态的数字仍更新，曲线保留已确认的历史。明确上游失败、超时、需重新登录、暂停或没有额度仍按错误提示。部分窗口缺失时仍展示其他已知窗口。

## 要求

- macOS 13 Ventura 或更高版本；从源码构建另需 Command Line Tools。
- 本机 OpenCodex 已安装、服务正在运行、至少登录一个 ChatGPT/Codex 账户；接入基线为 2.90.0。
- `ocx account list openai --quota --refresh --json` 可正常执行。
- 自动查找 `/opt/homebrew/bin`、`/usr/local/bin`、`~/.local/bin`、`~/.bun/bin` 和常见版本管理器目录，同时查找 `/Applications/OpenCodex.app/Contents/MacOS` 及用户 Applications 下的 sidecar，也支持进程继承的绝对 PATH 目录。启动 CLI 时补全 Node/Bun 常用 PATH，支持从 Finder 启动。

## 构建和安装更新

源码以 `main` 为准，维护记录见 [CHANGELOG.md](CHANGELOG.md)。安装包见 [codex-quota-bar Actions](https://github.com/Dylanx42/AI-Tools/actions/workflows/codex-quota-bar.yml) 中对应版本的成功构建；下载 artifact 需登录 GitHub。临时签名下载链接会过期，过期后从该次构建页面重新下载。

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

构建生成同时包含 Apple Silicon / Intel 的通用 App，使用 ad-hoc 签名，无第三方构建依赖。CI 在 macOS 构建、验证并打包 `Codex-Quota-Bar.zip`；先用 ditto 封装 App 以保留可执行权限，再验证解包后的签名。下载 Actions 的 `codex-quota-bar-macos` artifact 后，解开外层 artifact，再解开其中的 App ZIP，退出旧应用并将新 App 放入「应用程序」。CI 产物不替代本地安装与交互验收。当前没有自动更新器或开机自启功能。

当前采用 ad-hoc 签名，尚未配置 Developer ID 和 Apple 公证。如果自己确认来源的下载版本被 macOS 提示“Apple 无法验证”，可对安装好的本应用运行：

```sh
xattr -dr com.apple.quarantine "/Applications/Codex 额度栏.app"
open "/Applications/Codex 额度栏.app"
```

该命令只处理当前安装副本；以后下载覆盖的新版本可能需要再次执行，不代表已完成 Apple 公证。

## 本地记录与隐私

- 监控账户 ID 保存在应用的 `NSUserDefaults` 偏好中。
- 新趋势在 `~/Library/Application Support/CodexQuotaBar/opencodex-accounts/account-<账户ID的SHA256>.csv`，按账户 ID 隔离，不写邮箱或完整响应。`__main__` 对应主账户槽位；替换该槽位登录身份前，应备份并移出对应旧 CSV，避免不同身份并入同一槽位历史。
- 原有 `~/Library/Application Support/CodexQuotaBar/quota-history.csv` 完整保留，不自动迁入任何账户，因为旧版没有记录账户身份。
- 登录、管理令牌和账户凭据交给 OpenCodex CLI；额度栏不解析 `auth.json`、OpenCodex 凭据文件或 Keychain，不输出原始 CLI stderr，也不保存原始 JSON 响应。

详见 [PRIVACY.md](PRIVACY.md)、[SECURITY.md](SECURITY.md) 和 [接入决策](docs/decisions/0001-opencodex.md)。

## 验证与维护交接（2026-10-23）

本次 OpenCodex 接入、账户选择及后续修复集中在 [PR #26](https://github.com/Dylanx42/AI-Tools/pull/26)。每个版本的触发、行为和验证记录保存在变更日志，后续维护无需依赖旧聊天。

已确认的证据：

- 用户在 Mac 的 OpenCodex 2.90.0 验证了账户列表、当前账户及重置券查询，随后确认 0.6.1 重置券更新正常，并反馈额度新鲜度误报。用户也已对本机安装副本执行解除隔离命令；这不是公证或完整界面验收证据。
- 2026-10-23，macOS 14 arm64 的 [CI #57](https://github.com/Dylanx42/AI-Tools/actions/runs/39848023047) 已验证 0.6.2 的离线回归、Apple Silicon / Intel 双架构编译、签名及 ZIP 解包权限与签名。测试使用合成数据、模拟 CLI，不连接真实账户。
- 0.6.3 补充券状态与可用数量不一致的回归；2026-10-23 macOS 14 arm64 的 [CI #61](https://github.com/Dylanx42/AI-Tools/actions/runs/39855573108) 已通过离线回归、双架构构建、签名及 ZIP 解包检查并生成安装包。本次代码与文档在 Linux 云端维护，不能代替 Mac 实机验收。

Mac 本地待验收：

- Finder 启动后可找到 `ocx`，读取账户列表和当前额度；确认版本 0.6.3 / Build 21。
- 在「监控账户」选择 Plus / Pro，勾选和双窗口数据对应选择；重启 App 后记住选择，OpenCodex 实际选中账户未被额度栏切换。
- Pro 未返回 5 小时窗口时显示暂无数据；两账户曲线相互独立且旧 CSV 保留。
- 所选账户的重置券数量和到期时间与 `ocx account reset-credits <ID> --json` 一致；切换账户不会短暂显示另一账户的券。确认零券、未知和查询失败的区别；不执行兑换。
- Pro 账户缺少刷新状态时正常显示读到的额度，无橙色错误或重复错误段落；底部普通标注“上游状态未提供”。
- 停止服务、需重新登录或上游失败时仍正确报错，恢复服务后可刷新；深浅外观、悬停和重置标记正常。

源码发布不等于本地 App 已更新。后续维护从最新 `origin/main`、本 README 和变更记录开始。
