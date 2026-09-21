#!/bin/bash
# fix_blackhole_volume.sh — BlackHole 设备音量自动校正（防重启/重置后音量近零）
# 原理：临时把 BlackHole 设为默认输出 → osascript 拉满音量 → 还原原默认输出
set -e
SA="$(command -v SwitchAudioSource || echo /usr/local/bin/SwitchAudioSource)"
ORIG="$($SA -t output -c 2>/dev/null)"
$SA -t output -s "BlackHole 2ch" >/dev/null
osascript -e 'set volume output muted false' -e 'set volume output volume 100' >/dev/null
$SA -t output -s "$ORIG" >/dev/null
echo "BlackHole 音量已校正为 100（原默认输出 $ORIG 已还原）"
