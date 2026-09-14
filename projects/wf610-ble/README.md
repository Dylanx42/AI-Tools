# WF610 BLE

macOS 菜单栏工具：把 WAVARCL/Feasycom WF610A 的 BLE GATT 桥成持久虚拟串口，再交给 SecureCRT。关闭 CRT tab 不会断开 BLE。

```text
WF610BLE FFF0  <->  wf610-ble-bridge.py  <->  /tmp/ttyWF610BLE  <->  SecureCRT
```

## 功能

- 右上角菜单栏显示：未连接 / 连接中 / 已连接、连接时间、已连接时长。
- 手动开启连接、关闭连接、退出应用。
- 按已知 BLE 地址主动连接，不依赖扫描到广播名。
- SecureCRT 使用独立 session `console/WF610-BLE`，端口 `/tmp/ttyWF610BLE`。

## 实测设备

```text
BLE 名称: WF610BLE
BLE 地址: 56864941-4310-3722-B52D-EA59372A16B9
Classic:  WF610A / DC:0D:30:23:3D:E3 / /dev/cu.WF610A
模组:     Feasycom FSC-BT826B
Service:  FFF0
数据通知: FFF1
数据写入: FFF2
模组状态: FFF3（不进串口）
PIN:      0000
```

旧的 Classic SPP 脚本仍保留在 `scripts/connect-wf610a.sh` 和 `scripts/open-wf610a.sh`，不要和 BLE 桥接同时打开。

## 要求

- macOS 13 或更高版本
- Command Line Tools（构建菜单栏 App）
- Python 3.11 + `bleak`
- SecureCRT，session 名为 `console/WF610-BLE`，端口 `/tmp/ttyWF610BLE`，9600 8N1，流控全关

## 运行

本机日常用法：打开 `/Applications/WF610 BLE.app`，点菜单栏「开启连接」。

从源码启动桥接：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install bleak
./scripts/wf610-ble-open.sh
```

关闭：

```sh
./scripts/wf610-ble-stop.sh
```

## 构建

```sh
chmod +x build.sh
./build.sh
```

产物：`dist/WF610 BLE.app`

```sh
ditto "dist/WF610 BLE.app" "/Applications/WF610 BLE.app"
open -a "/Applications/WF610 BLE.app"
```

## 验证

```sh
plutil -lint Info.plist
./build.sh
codesign --verify --deep --strict --verbose=2 "dist/WF610 BLE.app"
```

## 项目结构

```text
.
├── Sources/WF610BLEApp.swift
├── scripts/
├── Info.plist
├── build.sh
├── README.md
├── PRIVACY.md
├── SECURITY.md
└── CHANGELOG.md
```

## 当前限制

- 菜单栏 App 优先使用 `~/WF610` 或本仓库 `scripts/` 下的桥接脚本。
- 仓库不提交 `.venv`、本机构建的 `.app` 或 SecureCRT 配置。
- ad-hoc 签名仅适合本机自用。
