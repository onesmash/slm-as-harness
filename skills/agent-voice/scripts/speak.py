#!/usr/bin/env python3
"""speak.py — 【内部调试工具，不是播放入口】直连合成：文本 → 本地 TTS → BlackHole 播放。

对外播放入口只有一个：`scripts/run.sh`（走 ttsd 常驻服务，见 SKILL.md「朗读文本」）。
本脚本绕开守护进程、自己开音频流，仅用于离线调试与历史兼容；不要把它当作
agent/用户可用的朗读方式，否则会绕开常驻服务（首音更慢、播放状态无人管理）。

用法（内部调试）:
    .venv-moss/bin/python speak.py "你好，这是本地合成语音"
    echo "多行文本会按句切分" | .venv-moss/bin/python speak.py -

链路: TTS(-o WAV, LEI16@48000) → sounddevice.OutputStream(BlackHole 2ch, low latency)
消费方 App 将 "BlackHole 2ch" 选为麦克风即可收音。
"""
import argparse
import pathlib
import subprocess
import sys
import threading
import tempfile
import time
import tomllib
import wave

import numpy as np
import sounddevice as sd

ROOT = pathlib.Path(__file__).resolve().parent
CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
ENGINE = CFG["engine"]
DEVICE = CFG["device"]

# HF 镜像必须在 transformers/hub 初始化前设置（模型下载镜像）
if ENGINE.get("hf_endpoint"):
    import os
    os.environ.setdefault("HF_ENDPOINT", ENGINE["hf_endpoint"])

_VOICE_CACHE = {}


def find_device(name_hint: str):
    """按名称包含匹配虚拟设备；未命中返回 (None, 列表)。"""
    hit, names = None, []
    for i in range(len(sd.query_devices())):
        d = sd.query_devices(i)
        names.append(d["name"])
        if name_hint.lower() in d["name"].lower() and d["max_output_channels"] > 0:
            hit = i
            break
    return hit, names


def _resample_to_48k_stereo(raw_wav: str) -> tuple[np.ndarray, int]:
    """sox 一次性高质量重采样到 48k 立体声（report.md T3 约定）。"""
    out = raw_wav.replace(".wav", "_48k.wav")
    subprocess.run(["sox", raw_wav, "-r", "48000", "-c", "2", out, "rate", "-v"],
                   check=True, capture_output=True)
    with wave.open(out, "rb") as w:
        sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.reshape(-1, 2), sr



def synthesize_say(text: str) -> tuple[np.ndarray, int]:
    """零安装兜底: say → WAV(LEI16@48k) → numpy int16 立体声。"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    subprocess.run(
        ["say", "-v", ENGINE["voice"], "-o", wav_path,
         "--data-format", ENGINE["format"], text],
        check=True,
    )
    with wave.open(wav_path, "rb") as w:
        sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        if w.getnchannels() == 1:
            pcm = np.stack([pcm, pcm], axis=1)  # 双声道复制，匹配 BlackHole 2ch
    pathlib.Path(wav_path).unlink(missing_ok=True)
    return pcm, sr


def synthesize(text: str) -> tuple[np.ndarray, int]:
    """按 config.toml 的 engine.name 分发。"""
    if ENGINE["name"] == "moss":
        from text_pipeline import normalize_numbers
        text = normalize_numbers(text)   # 直连路径与 ttsd 路径归一化一致
        if "moss" not in _VOICE_CACHE:
            from moss_engine import MossEngine, resolve_platform_threads
            _VOICE_CACHE["moss"] = MossEngine(
                prompt_audio=ENGINE.get("prompt_audio", "assets/audio/zh_1.wav"),
                thread_count=resolve_platform_threads(ENGINE.get("threads", 4)))
        return _VOICE_CACHE["moss"].synth(text)
    return synthesize_say(text)


def play_to_loopback(pcm: np.ndarray, sr: int) -> None:
    dev, names = find_device(DEVICE["name"])
    if dev is None:
        sys.exit(f"[speak] 找不到输出设备 {DEVICE['name']!r}；当前设备: {names}")
    ch = pcm.shape[1]

    def make_stream(dev_idx):
        return sd.OutputStream(
            device=dev_idx, samplerate=sr, channels=ch, dtype="int16",
            blocksize=int(DEVICE["blocksize"]), latency=DEVICE["latency"],
        )

    streams = [("BlackHole", make_stream(dev))]

    # monitor 同播：同时在本地默认输出设备播放一份（人工确认用）
    if CFG.get("monitor", {}).get("enabled", False):
        mname = CFG["monitor"].get("name", "auto")
        if mname == "auto":
            mdev = None  # 系统默认输出
        else:
            mdev, _ = find_device(mname)
        streams.append((f"monitor:{mname}", make_stream(mdev)))

    for tag, s in streams:
        s.start()
    sd.sleep(50)  # 预热，稳定设备时钟
    errs = []

    def feed(tag, s):
        try:
            s.write(pcm)       # 阻塞写完（整段朗读）
        except Exception as e:
            errs.append(f"{tag}: {e}")

    ths = [threading.Thread(target=feed, args=(t, s)) for t, s in streams]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    for _, s in streams:
        s.stop()
        s.close()
    if errs:
        print(f"[speak] 播放告警: {'; '.join(errs)}")
    print(f"[speak] 同播设备: {', '.join(t for t, _ in streams)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="text → say → BlackHole")
    ap.add_argument("text", help='要朗读的文本；"-" 则从 stdin 读取')
    args = ap.parse_args()
    text = sys.stdin.read() if args.text == "-" else args.text
    if not text.strip():
        sys.exit("[speak] 空文本")
    t0 = time.perf_counter()
    pcm, sr = synthesize(text.strip())
    t1 = time.perf_counter()
    play_to_loopback(pcm, sr)
    dur = len(pcm) / sr
    print(f"[speak] 合成 {t1-t0:.2f}s | 音频时长 {dur:.2f}s | RTF≈{(t1-t0)/dur:.2f} | "
          f"输出 {DEVICE['name']} @ {sr}Hz bs={DEVICE['blocksize']}")


if __name__ == "__main__":
    main()
