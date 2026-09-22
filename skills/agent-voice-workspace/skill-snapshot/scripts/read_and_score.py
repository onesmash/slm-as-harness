#!/Users/xuhui/Code/research/research-output/tts-mic-loopback/deployment/.venv-moss/bin/python
"""read_and_score.py — 朗读→录音→STT→CER 闭环第一步。

流程:
  1. 从 BlackHole 输入端同步录音（48k）
  2. 调 ttsay 朗读指定文本（守护进程流式合成+播放）
  3. 保存录音 → /tmp/loop_capture.wav
用法:
  .venv-moss/bin/python read_and_score.py <文本文件> <输出前缀>
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

ROOT = Path(__file__).resolve().parent
TEXT_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/wx_article.txt")
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "loop"


def find_bh_input():
    from text_pipeline import find_bh_input as _find
    idx = _find()
    if idx is None:
        raise RuntimeError("BlackHole input not found")
    return idx


def main():
    text_file = Path(TEXT_FILE)
    text = text_file.read_text().strip()
    print(f"[loop] 文本 {len(text)} 字符，来自 {text_file}", flush=True)

    buf = []
    dev = find_bh_input()
    st = sd.InputStream(device=dev, samplerate=48000, channels=2, dtype="int16",
                        blocksize=256, latency="low",
                        callback=lambda i, f, t, s: buf.append(i.copy()))
    st.start()
    t0 = time.perf_counter()
    print("[loop] 开始朗读（守护进程流式）...", flush=True)

    import socket
    SOCK = ROOT / "ttsd.sock"
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(str(SOCK))
    s.sendall(json.dumps({"text": text}).encode() + b"\n")
    f = s.makefile("rb")
    first_audio = None
    for line in f:
        ev = json.loads(line)
        if ev["event"] == "playback_started":
            first_audio = (time.perf_counter() - t0) * 1000
            print(f"[loop] 首音 {first_audio:.0f}ms", flush=True)
        elif ev["event"] == "done":
            print(f"[loop] 朗读完成：音频 {ev['audio_seconds']}s / 合成 {ev['synth_seconds']}s", flush=True)
            break
    s.close()
    time.sleep(1.0)          # 尾部余量
    st.stop(); st.close()
    total = time.perf_counter() - t0

    import wave
    pcm = np.concatenate(buf).astype(np.int16)
    wav = f"/tmp/{PREFIX}_capture.wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(pcm.tobytes())
    mono = pcm.astype(np.float32).reshape(-1, 2).mean(axis=1) / 32768
    rms = float(np.sqrt(np.mean(mono ** 2)))
    print(f"[loop] 录音 {len(mono)/48000:.1f}s RMS={rms:.4f} → {wav}", flush=True)

    meta = {"text_file": str(text_file), "chars": len(text), "capture": wav,
            "capture_seconds": len(mono) / 48000, "rms": rms,
            "first_audio_ms": first_audio, "total_wall_s": total}
    Path(f"/tmp/{PREFIX}_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
