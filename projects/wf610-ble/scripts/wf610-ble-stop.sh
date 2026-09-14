#!/bin/zsh
# 停掉 BLE 桥接，并清掉虚拟串口/状态文件
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRIDGE="$SCRIPT_DIR/wf610-ble-bridge.py"

if pgrep -f "$BRIDGE" >/dev/null 2>&1; then
    pkill -f "$BRIDGE" >/dev/null 2>&1 || true
    sleep 1
    pkill -9 -f "$BRIDGE" >/dev/null 2>&1 || true
    print "已停止 BLE 桥接"
else
    print "桥接本来就没在跑"
fi

for f in /tmp/ttyWF610BLE /tmp/cu.WF610BLE /tmp/wf610-ble-bridge.state; do
    [[ -e "$f" || -L "$f" ]] && rm -f "$f"
done
