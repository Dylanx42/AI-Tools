#!/bin/zsh
set -euo pipefail

PROJECT_DIR="${0:A:h}"
OUTPUT_ROOT="$PROJECT_DIR/dist"
APP_NAME="Codex 额度栏.app"
APP_DIR="$OUTPUT_ROOT/$APP_NAME"
MODULE_CACHE="$PROJECT_DIR/.build/module-cache"

mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$MODULE_CACHE"

/usr/bin/clang \
  -fobjc-arc \
  -fmodules \
  -O2 \
  -mmacosx-version-min=13.0 \
  -fmodules-cache-path="$MODULE_CACHE" \
  -framework Cocoa \
  "$PROJECT_DIR/Sources/main.m" \
  -o "$APP_DIR/Contents/MacOS/CodexQuotaBar"

/bin/cp "$PROJECT_DIR/Info.plist" "$APP_DIR/Contents/Info.plist"
/usr/bin/codesign --force --deep --sign - "$APP_DIR"

echo "$APP_DIR"
