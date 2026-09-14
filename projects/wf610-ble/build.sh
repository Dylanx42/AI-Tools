#!/bin/zsh
set -euo pipefail

PROJECT_DIR="${0:A:h}"
OUTPUT_ROOT="$PROJECT_DIR/dist"
APP_NAME="WF610 BLE.app"
APP_DIR="$OUTPUT_ROOT/$APP_NAME"
MODULE_CACHE="$PROJECT_DIR/.build/module-cache"
BIN="$APP_DIR/Contents/MacOS/WF610BLE"

mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources" "$MODULE_CACHE"

/usr/bin/swiftc \
  -parse-as-library \
  -O \
  -module-cache-path "$MODULE_CACHE" \
  -framework Cocoa \
  "$PROJECT_DIR/Sources/WF610BLEApp.swift" \
  -o "$BIN"

/bin/cp "$PROJECT_DIR/Info.plist" "$APP_DIR/Contents/Info.plist"
printf 'APPL????' > "$APP_DIR/Contents/PkgInfo"
/usr/bin/codesign --force --deep --sign - "$APP_DIR"
echo "$APP_DIR"
