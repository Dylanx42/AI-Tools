#!/bin/zsh
set -euo pipefail
PROJECT_DIR="${0:A:h}"
APP_DIR="$PROJECT_DIR/dist/IP 快捷设置.app"
mkdir -p "$APP_DIR/Contents/MacOS" "$PROJECT_DIR/.build/module-cache"
/usr/bin/swiftc -target "$(/usr/bin/uname -m)-apple-macosx13.0" -O -module-cache-path "$PROJECT_DIR/.build/module-cache" -framework Cocoa -framework SystemConfiguration "$PROJECT_DIR/Sources/IPSwitcher.swift" -o "$APP_DIR/Contents/MacOS/IPSwitcher"
/bin/cp "$PROJECT_DIR/Info.plist" "$APP_DIR/Contents/Info.plist"
printf 'APPL????' > "$APP_DIR/Contents/PkgInfo"
/usr/bin/codesign --force --deep --sign - "$APP_DIR"
echo "$APP_DIR"
