#!/bin/zsh
set -euo pipefail
PROJECT_DIR="${0:A:h}"
mkdir -p "$PROJECT_DIR/.build/module-cache"
/usr/bin/clang -fobjc-arc -fmodules -Wall -Wextra -Wno-unused-parameter \
  -mmacosx-version-min=13.0 \
  -fmodules-cache-path="$PROJECT_DIR/.build/module-cache" \
  -framework Cocoa "$PROJECT_DIR/Tests/main.m" "$PROJECT_DIR/Sources/OpenCodexQuota.m" \
  -o "$PROJECT_DIR/.build/quota-tests"
"$PROJECT_DIR/.build/quota-tests"
