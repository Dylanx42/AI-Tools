#!/bin/zsh
# 本地 App 入口：没连上就打开，已连上就关闭
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE="/tmp/wf610-ble-bridge.state"
PORT="/tmp/ttyWF610BLE"
BRIDGE="$SCRIPT_DIR/wf610-ble-bridge.py"

bridge_running() {
    pgrep -f "$BRIDGE" >/dev/null 2>&1
}

state_name() {
    [[ -f "$STATE" ]] || return 1
    awk '{print $1}' "$STATE" 2>/dev/null
}

ble_connected() {
    bridge_running || return 1
    [[ -e "$PORT" ]] || return 1
    [[ "$(state_name)" == connected ]]
}

if ble_connected; then
    "$SCRIPT_DIR/wf610-ble-stop.sh"
    exit 0
fi
exec "$SCRIPT_DIR/wf610-ble-open.sh"
