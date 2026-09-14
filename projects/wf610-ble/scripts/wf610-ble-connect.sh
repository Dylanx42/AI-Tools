#!/bin/zsh
# 启动 WF610 BLE -> 持久虚拟串口桥接。
# 不清理 macOS RFCOMM 缓存，不重启 blued；BLE 与 CRT 会话解耦。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
    print -u2 "ERROR: 找不到 python3；可用 WF610_PYTHON 指定解释器"
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import bleak' 2>/dev/null; then
    print -u2 "ERROR: $PYTHON_BIN 没有 bleak"
    print -u2 "请把 bleak 安装到这个 Python 环境，或用 WF610_PYTHON 指向已安装 bleak 的环境"
    exit 1
fi

exec "$PYTHON_BIN" -u "$SCRIPT_DIR/wf610-ble-bridge.py" "$@"
