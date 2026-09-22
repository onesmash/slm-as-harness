#!/bin/bash
# run.sh — 推荐入口：走常驻服务（首音延迟 150-370ms 热态 / ~5s 冷启动）
#          停止服务: launchctl unload ~/Library/LaunchAgents/com.moss.ttsd.plist
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv-moss/bin/python" "$DIR/ttsay.py" "$@"
