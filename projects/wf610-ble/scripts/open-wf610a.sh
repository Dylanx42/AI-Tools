#!/bin/bash
# open-wf610a.sh - 清理蓝牙缓存，释放串口（不杀 CRT 进程）
PORT="/dev/cu.WF610A"
BT_PLIST="/Library/Preferences/com.apple.Bluetooth.plist"
TARGET_ADDR="DC:0D:30:23:3D:E3"

# 1. 检查串口是否被占用
PIDS=$(lsof "$PORT" 2>/dev/null | awk 'NR>1 {print $2}' | sort -u)
if [ -n "$PIDS" ]; then
    echo "⚠️  串口被以下进程占用："
    lsof "$PORT" 2>/dev/null | awk 'NR>1 {print "   PID:", $2, "进程:", $1}'
    echo ""
    echo "请先在 CRT 里关闭这个 session（右键 tab → Close），然后重新运行此脚本"
    exit 1
fi

# 2. 清理 RFCOMM 缓存并重启蓝牙
sudo defaults delete "$BT_PLIST" "PersistentPorts:$TARGET_ADDR" 2>/dev/null
echo "✅ 已清理 RFCOMM 缓存"

# 3. 重启蓝牙服务
echo "🔄 重启蓝牙服务..."
sudo pkill -HUP blued 2>/dev/null || sudo pkill -f bluetoothd 2>/dev/null
sleep 2

# 3. 等待串口就绪（最多等 15 秒）
echo "⏳ 等待串口就绪..."
for i in $(seq 1 15); do
    if [ -e "$PORT" ] && [ ! "$(lsof "$PORT" 2>/dev/null | grep -v '^COMMAND')" ]; then
        echo "✅ WF610A 串口就绪，可以连接了（耗时 ${i}s）"
        exit 0
    fi
    sleep 1
done

echo "❌ 串口未就绪，请检查蓝牙连接或手动重试"
exit 1
