#!/usr/bin/env python3
"""ttsay.py — ttsd 常驻服务客户端。守护进程未启动时自动等待 launchd 拉起。

用法:
  ./ttsay.py "要朗读的文本"    # 朗读（阻塞至播放完成）
  ./ttsay.py --stop            # 停止当前播放（可从另一个终端/连接发起）
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
    argv = sys.argv[1:]
    stop_mode = "--stop" in argv
    argv = [a for a in argv if a != "--stop"]
    if not stop_mode and len(argv) < 1:
        sys.exit('用法: ./ttsay.py "要朗读的文本" | ./ttsay.py --stop')
    ensure_daemon()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(str(SOCK))
    if stop_mode:
        s.sendall(json.dumps({"cmd": "stop"}).encode() + b"\n")
        f = s.makefile("rb")
        for line in f:
            ev = json.loads(line)
            if ev["event"] == "ready":
                continue   # serve 在 recv 循环前先发 ready，停止应答在其后
            if ev["event"] in ("stopped", "done"):
                print("[ttsay] ⏹ 停止指令已送达", flush=True)
                break
        s.close()
        return

    s.sendall(json.dumps({"text": argv[0]}).encode() + b"\n")

    f = s.makefile("rb")
    for line in f:
        ev = json.loads(line)
        if ev["event"] == "playback_started":
            print(f"[ttsay] 🔊 开始播放（文本提交→首音 {ev['first_audio_ms']}ms）", flush=True)
        elif ev["event"] == "stopped":
            print("[ttsay] ⏹ 播放已被停止", flush=True)
            break
        elif ev["event"] == "done":
            mark = "（被停止）" if ev.get("stopped") else ""
            print(f"[ttsay] 完成{mark}：音频 {ev['audio_seconds']}s / 合成 {ev['synth_seconds']}s / "
                  f"{ev['sentences']} 句", flush=True)
            break   # 本次朗读结束即退出（守护进程常驻）
        elif ev["event"] == "ready":
            pass
    s.close()


if __name__ == "__main__":
    main()
