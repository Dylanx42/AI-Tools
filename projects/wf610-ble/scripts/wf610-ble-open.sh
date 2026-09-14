#!/bin/zsh
# 一键：按已知地址主动连接 WF610BLE，连上后再打开 CRT
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="/tmp/ttyWF610BLE"
SESSION="console/WF610-BLE"
LOG="/tmp/wf610-ble-bridge.log"
STATE="/tmp/wf610-ble-bridge.state"
BRIDGE="$SCRIPT_DIR/wf610-ble-bridge.py"
WAIT_SECS=20

if [[ -n "${WF610_PYTHON:-}" ]]; then
    PYTHON_BIN="$WF610_PYTHON"
elif [[ -x "$SCRIPT_DIR/../.venv/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/../.venv/bin/python"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
    PYTHON_BIN="$(command -v python3 2>/dev/null || true)"
fi

if [[ -z "$PYTHON_BIN" || ! -x "$PYTHON_BIN" ]]; then
    print -u2 "ERROR: 找不到 python3"
    exit 1
fi
if ! "$PYTHON_BIN" -c 'import bleak' 2>/dev/null; then
    print -u2 "ERROR: $PYTHON_BIN 没有 bleak"
    exit 1
fi

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

start_bridge() {
    print "按已知地址主动连接 WF610BLE..."
    : > "$LOG"
    print -n "connecting" > "$STATE"
    nohup "$PYTHON_BIN" -u "$BRIDGE" --state-file "$STATE" >> "$LOG" 2>&1 &
    disown
}

if ! ble_connected; then
    if bridge_running; then
        print "发现未连上的旧桥接，先停掉再主动连接"
        "$SCRIPT_DIR/wf610-ble-stop.sh" >/dev/null 2>&1 || true
        sleep 1
    fi
    start_bridge
    ready=0
    for i in $(seq 1 "$WAIT_SECS"); do
        if ble_connected; then
            ready=1
            break
        fi
        sleep 1
    done
    if [[ "$ready" -ne 1 ]]; then
        print -u2 "ERROR: ${WAIT_SECS}s 内没有连上 WF610BLE"
        print -u2 "当前状态: $(cat "$STATE" 2>/dev/null || echo none)"
        print -u2 "看日志: $LOG"
        tail -n 50 "$LOG" 2>/dev/null || true
        exit 1
    fi
fi

print "BLE 已连接: $PORT"
open -a "SecureCRT" --args "/S" "$SESSION"
print "已打开 CRT session: $SESSION"
print "抓完 log 直接关 tab。停桥接: $SCRIPT_DIR/wf610-ble-stop.sh"
