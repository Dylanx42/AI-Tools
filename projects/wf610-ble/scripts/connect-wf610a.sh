#!/bin/bash
# connect-wf610a.sh - 一键清理 + 打开 CRT session
# 用法: bash ~/connect-wf610a.sh

# 1. 运行清理脚本
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
bash "$SCRIPT_DIR/open-wf610a.sh"

# 2. 打开 CRT session
open -a "SecureCRT" --args "/S" "console/Serial-cu.WF610A"
