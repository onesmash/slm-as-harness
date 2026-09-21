#!/Users/xuhui/Code/research/.venv-dwr/bin/python
"""ttsay.py — ttsd 常驻服务客户端。守护进程未启动时自动拉起。

用法: ./ttsay.py "要朗读的文本"
"""
import json
import pathlib
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOCK = pathlib.Path.home() / ".config" / "agent-voice" / "ttsd.sock"


def ensure_daemon():
    if SOCK.exists():
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(str(SOCK))
            s.close()
            return
        except OSError:
            pass
    # launchd 是守护进程的唯一管理器（KeepAlive 自愈）；客户端只等待，绝不 spawn
    # （多管理器实例风暴是今晚事故根因，见 DEPLOYMENT.md §6.13）
    for _ in range(60):
        if SOCK.exists():
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(str(SOCK))
                s.close()
                return
            except OSError:
                pass
        time.sleep(1)
    sys.exit("[ttsay] 守护进程未运行。启动: launchctl load ~/Library/LaunchAgents/com.moss.ttsd.plist")


def main():
    if len(sys.argv) < 2:
        sys.exit('用法: ./ttsay.py "要朗读的文本"')
    ensure_daemon()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(str(SOCK))
    s.sendall(json.dumps({"text": sys.argv[1]}).encode() + b"\n")

    f = s.makefile("rb")
    for line in f:
        ev = json.loads(line)
        if ev["event"] == "playback_started":
            print(f"[ttsay] 🔊 开始播放（文本提交→首音 {ev['first_audio_ms']}ms）", flush=True)
        elif ev["event"] == "done":
            print(f"[ttsay] 完成：音频 {ev['audio_seconds']}s / 合成 {ev['synth_seconds']}s / "
                  f"{ev['sentences']} 句", flush=True)
            break   # 本次朗读结束即退出（守护进程常驻）
        elif ev["event"] == "ready":
            pass
    s.close()


if __name__ == "__main__":
    main()
