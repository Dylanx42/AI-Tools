# Codex 额度栏：功能验证入口与证据表

适用当前 OpenCodex CLI → 账户/额度模型 → 菜单栏控制器与账户独立 CSV 的路线。
复用 [test.sh](../../test.sh)、[Tests/main.m](../../Tests/main.m)、[build.sh](../../build.sh) 和
[macOS CI](../../../../.github/workflows/codex-quota-bar.yml)，不增加测试框架或连接真实账户的前置要求。

## 1. 选择验证层级

| 层级 | 入口与准备 | 能证明什么 / 边界 |
| --- | --- | --- |
| 离线源码回归 | macOS 13+、Command Line Tools；从当前工作区执行 `./test.sh` | 五组映射、控制器/历史和模拟 CLI 检查；不需要 OpenCodex 登录，不启动菜单栏 App |
| 构建与交付包 | `./build.sh`、plist、签名、架构、ZIP 解包检查 | 本次源码构建及打包完整性；ad-hoc 签名不等于 Developer ID/Apple 公证，含 x86_64 不等于 Intel 实机已运行 |
| 真实账户与已安装 App | 核对 App 路径、版本/Build、OpenCodex 版本及服务状态；使用[README 的本地验收清单](../../README.md#验证与维护交接2026-10-23) | Finder 启动、实际 CLI 查找、登录兼容、重启记忆、菜单/图表交互；需要单独记录 |

当前源码版本见 [Info.plist](../../Info.plist)。源码、工作区构建和已安装 App 是三个对象，不能凭版本文字相同
就认定来自同一提交。记录 Git 提交、实际 App/可执行路径和包 Hash；源码 PR 不自动更新 `/Applications`。

## 2. 功能验证表

“已有检查”表示可复跑的入口，只有实际执行后才能对该提交/平台记 PASS。
本表描述现有覆盖，不把尚未覆盖的 UI 或外部状态升级成自动化通过。

| 路径 | 用户目标与操作入口 | 可观察的通过条件 | 已有检查 | 剩余边界 |
| --- | --- | --- | --- | --- |
| F1 打开后读取额度 | 启动 App，查看短/长窗口；点击“立即刷新” | 已用比例正确转为剩余；缺失短窗口保持未知；月窗口有正确周期；无数据不伪装成 100% | `TestMapping`；`TestCLI` 检查指定模拟可执行文件和账户查询参数 | Finder 的 CLI 自动查找、真实登录/API 兼容及实际菜单显示待实机核验 |
| F2 选择监控账户 | “监控账户”菜单选择另一账户，关闭再打开 App | 初次按当前账户选取；明确选择不跟随 active 变化；偏好保存；读取中不接受再次切换；已移除账户要求重选 | `TestMapping`、`TestControllerAndHistory` 检查选择、偏好写入/读回和账户移除 | 测试没有真正重启 App；重启记忆、菜单勾选及 OpenCodex 实际路由账户未改变需现场核验 |
| F3 查看趋势并处理未知/失败 | 切换账户、刷新后查看各自趋势 | 账户 CSV 隔离；外来账户快照不写入；旧 CSV 保留；失败/未确认新鲜度不追加；缺少刷新元数据仍更新额度且不进入失败退避；明确 ok 后恢复写入 | `TestControllerAndHistory`、`TestMapping` | 断言覆盖数据与控制器状态，不能证明图表实际绘制；真实历史目录权限与长期记录仍需现场核验 |
| F4 查看重置券 | 当前监控账户的券数量和最近到期时间，切换账户后继续查看 | 区分零张、未知、日期缺失；只统计可用券；数量/无状态日期不一致时不猜日期；旧账户迟到响应丢弃；券查询失败不影响额度 | `TestResetCreditsMapping`、`TestResetCreditsCLI`、`TestControllerAndHistory`；模拟子进程核对只读参数 | 真实 OpenCodex 版本的数量/日期与界面需比对；不兑换重置券来制造样例 |
| F5 查询异常与取消 | CLI 缺失、返回错误、超限、超时或查询取消后查看状态 | 分类拒绝错误数据；回调在主线程且只完成一次；取消后不回调旧结果 | `TestCLI` 覆盖无可执行文件、非法 JSON、非零退出、2 MiB+1 输出、短测试超时和取消；`TestResetCreditsCLI` 拒绝选项形态账户 ID | 测试用明确的模拟路径/短时限，不能代替真实服务故障恢复或生产 60/15 秒时限的墙钟验证 |
| F6 自动刷新与唤醒 | 持续使用、低电量、休眠唤醒、打开菜单 | 按 README 规定调整间隔；唤醒及菜单数据过旧时刷新 | 控制器测试经过调度逻辑并检查缺元数据时的失败计数；实现见 `nextSuccessfulRefreshIntervalChanged:`、`nextFailureRefreshInterval`、`workspaceDidWake:` | 现有测试没有逐一断言全部间隔，也未驱动真实低电量/唤醒/菜单事件，保持待验收 |
| F7 图表、悬停与外观 | 移动鼠标查看最近采样点，切换深浅外观 | 双窗口数值、重置标记、时间/周期、悬停定位和可读性符合预期 | 构建会编译绘图代码；`HeadlessDelegate` 明确跳过菜单/状态栏更新 | 无自动化绘图/鼠标/截图验收，不能从测试 PASS 推导；按 README 实机清单核对 |
| F8 交付与安装 | 从本次源码生成 App/ZIP，解包后交付 | plist 有效；双架构存在；原包/解包签名有效；二进制可执行；内容/版本与构建一致 | `build.sh` 与下方 CI 同类命令 | 安装、Finder 启动、Gatekeeper、真实账户、Intel 运行另记；本流程不覆盖已安装版本 |

数据映射、账户选择及历史的实现入口见 [OpenCodexQuota.m](../../Sources/OpenCodexQuota.m) 和
[main.m](../../Sources/main.m)。接口选择与刷新含义以[接入决策](../decisions/0001-opencodex.md)为准。

## 3. 复用五组既有测试

`./test.sh` 编译本机架构的 `.build/quota-tests` 并执行以下函数；没有单组筛选参数。
测试使用真实实现，外部 CLI 通过显式路径替换为临时可执行脚本；控制器服务用 stub 提供响应。
这两种边界分别验证，不是启动 App 后连通真实服务的端到端测试。

| 测试函数（均在 Tests/main.m） | 重点 |
| --- | --- |
| `TestMapping` | 短/周/月窗口、缺失/非法字段、新鲜度状态、选择和账户文件名 |
| `TestResetCreditsMapping` | 可用券、数量/日期一致性、零/未知和失败文案 |
| `TestControllerAndHistory` | 一条读取 → 失败 → 切换 → 丢弃迟到券 → 新账户采样 → 未确认/失败不写入 → 恢复 → 移除账户的完整离线状态流程 |
| `TestCLI` | 真实 NSTask 启动模拟 CLI，精确参数、JSON、错误、输出上限、超时与取消 |
| `TestResetCreditsCLI` | 模拟券查询的精确只读参数、返回值及非法账户 ID 拒绝 |

测试给控制器设置独立 `quota-tests.<UUID>` 偏好域和临时 CSV 目录，正常结束时移除偏好域、临时数据并停止定时器。
`HeadlessDelegate` 不注册菜单栏或渲染窗口。测试日志中的模拟错误是预期分支；判断结果看退出码和末尾
`PASS: OpenCodex quota/reset-credit mapping...`。测试框架不输出逐条计数，不把源码中的 Check 调用数当作测试结果数量。

## 4. 完整离线复跑与交付包核验

在最新 main 的独立工作区，从 `projects/codex-quota-bar/` 运行。先记录 `git rev-parse HEAD`、
`git status --short`、`sw_vers`、`uname -m`、`xcode-select -p`、`xcrun --show-sdk-version` 和 `clang --version`。
此路径无需启动 OpenCodex、读取真实账户或覆盖已安装 App。

以下为 zsh/bash 命令。将 `QUOTA_RUN` 替换为父目录已存在、目标尚不存在的绝对目录。
建议放在主 checkout 的 `.build/verification/<唯一运行名>/` 或工作区之外的私有目录；保留完整日志。

```bash
set -euo pipefail
QUOTA_RUN="/绝对路径/新的额度栏验证目录"
mkdir "$QUOTA_RUN"
plutil -lint Info.plist > "$QUOTA_RUN/plist.log" 2>&1
./test.sh > "$QUOTA_RUN/test.log" 2>&1
./build.sh > "$QUOTA_RUN/build.log" 2>&1
codesign --verify --deep --strict --verbose=2 "dist/Codex 额度栏.app" > "$QUOTA_RUN/signature.log" 2>&1
for QUOTA_ARCH in arm64 x86_64; do
  /usr/bin/lipo "dist/Codex 额度栏.app/Contents/MacOS/CodexQuotaBar" -verify_arch "$QUOTA_ARCH" > "$QUOTA_RUN/arch-$QUOTA_ARCH.log" 2>&1
done
ditto -c -k --sequesterRsrc --keepParent "dist/Codex 额度栏.app" "$QUOTA_RUN/Codex-Quota-Bar.zip"
ditto -x -k "$QUOTA_RUN/Codex-Quota-Bar.zip" "$QUOTA_RUN/unpacked"
test -x "$QUOTA_RUN/unpacked/Codex 额度栏.app/Contents/MacOS/CodexQuotaBar"
codesign --verify --deep --strict --verbose=2 "$QUOTA_RUN/unpacked/Codex 额度栏.app" > "$QUOTA_RUN/unpacked-signature.log" 2>&1
for QUOTA_ARCH in arm64 x86_64; do
  /usr/bin/lipo "$QUOTA_RUN/unpacked/Codex 额度栏.app/Contents/MacOS/CodexQuotaBar" -verify_arch "$QUOTA_ARCH" > "$QUOTA_RUN/unpacked-arch-$QUOTA_ARCH.log" 2>&1
done
diff -qr "dist/Codex 额度栏.app/Contents" "$QUOTA_RUN/unpacked/Codex 额度栏.app/Contents"
shasum -a 256 "$QUOTA_RUN/Codex-Quota-Bar.zip" > "$QUOTA_RUN/archive.sha256"
```

逐架构执行与同时核验两架构的目标相同。本机 macOS 27.2 上一次多参数 `-verify_arch arm64 x86_64`
报参数错误，逐一检查通过，详见[本次记录](2026-10-31-entry.md)；不要忽略失败后直接宣称双架构通过。
现有 CI 仍采用其 macOS runner 上的原命令，未因本机差异修改 CI。

成功标准：各命令退出 0，测试有最终 PASS，签名有效，两个架构分别通过，解包二进制可执行且 Contents 内容一致。
失败时保留日志、退出码和已生成文件，先区分工具环境、测试失败和打包失败；复跑使用新证据目录。
不要通过删断言、忽略退出码、换用已安装旧 App 或解除隔离标记来掩盖验证失败。

## 5. 真实账户和桌面验收

按 [README 本地清单](../../README.md#验证与维护交接2026-10-23)核对 F1–F7，记录实际 App、OpenCodex、macOS
版本和操作前后可观察结果。历史 OpenCodex 2.90.0 记录仅是当时的接入证据，不是当前版本兼容结论。

- 验证账户选择时，检查选择前后额度栏监控对象和 OpenCodex 实际当前账户；只改变额度栏选择。
- 券信息用现有只读查询比对，保留脱敏摘要；零券/无数据/失败无法自然复现时记录待验收。
- 故障、超时、迟到响应优先用现有模拟测试。真实服务故障恢复在隔离测试环境进行，不为制造样例中断日常服务。
- 真实查询可能刷新 OpenCodex 的额度缓存；安装及首次运行也可能改变额度栏偏好和 CSV，不能将其视作零副作用检查。

完整账户响应、账户 ID、凭据和真实历史 CSV 不放进 PR；遵循 [Privacy](../../PRIVACY.md) 与
[Security](../../SECURITY.md)。界面证据先脱敏。测试成功后的临时 CSV 已被清理，不能假称留存了这些原件；
保留的证据是测试日志、提交/环境、构建包与其核验结果。失败提前退出可能留下测试临时目录/偏好域，先辨认再清理。

每次交付记录日期/平台、被测提交与实际路径、涉及 F1–F8、命令/退出码、包 Hash、通过/失败/未执行和原因。
在 [CHANGELOG](../../CHANGELOG.md)保留触发、结果和剩余工作，详细实跑记录放在本目录。
新增功能或变更接口时更新对应行与测试；缺少桌面或服务证据时保持待验收，不用构建成功替代。
