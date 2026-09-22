#!/usr/bin/env python3
"""ttsd.py — 常驻 TTS 服务（report.md T7 形态 B/C）。

模型只加载一次并预热；文本经 Unix domain socket 进来，按句切分后
流水线合成（有界队列），首句合成完立即开播（低首音延迟），
同时写 BlackHole（虚拟麦克风）与本地默认输出（monitor 同播）。

协议（UDS + JSON-lines）:
    发送: {"text": "要朗读的文本"}   （一行一条）
    接收: {"event": "ready"}         服务就绪
          {"event": "playback_started", "first_audio_ms": 123.4}
          {"event": "done", "audio_seconds": 5.4, "synth_seconds": 0.4}

启动: ./ttsd.py &   停止: pkill -f ttsd.py
"""
import json
import os
import queue
import re
import socket
import sys
import threading
import subprocess
import wave
import time
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
STATE_DIR = pathlib.Path.home() / ".config" / "agent-voice"   # 运行时状态：配置/日志/锁/socket
STATE_DIR.mkdir(parents=True, exist_ok=True)
SOCK = STATE_DIR / "ttsd.sock"
import numpy as _np
import numpy as np
BH_GAIN = {"v": 1.0}

# HF 镜像必须在 transformers/hub 初始化前设置
# 配置解析：内置 scripts/config.toml 为基底，~/.config/agent-voice/config.toml 逐键覆盖（用户优先）
from config_loader import load_config
CFG, _CFG_PATH = load_config(ROOT / "config.toml", STATE_DIR / "config.toml")
if CFG["engine"].get("hf_endpoint"):
    os.environ.setdefault("HF_ENDPOINT", CFG["engine"]["hf_endpoint"])

import numpy as np
import sounddevice as sd


def log(msg):
    print(f"[ttsd {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def open_output(name_hint=None, retries=5):
    """开输出流；name_hint=None 为系统默认输出（monitor）。带 -10863 重试。"""
    for k in range(retries):
        try:
            dev = None
            if name_hint:
                for i in range(len(sd.query_devices())):
                    d = sd.query_devices(i)
                    if name_hint.lower() in d["name"].lower() and d["max_output_channels"] >= 2:
                        dev = i
                        break
                if dev is None:
                    raise RuntimeError(f"设备未找到: {name_hint}")
            st = sd.OutputStream(device=dev, samplerate=48000, channels=2,
                                 dtype="int16", blocksize=int(CFG["device"]["blocksize"]),
                                 latency=CFG["device"]["latency"])
            st.start()
            return st
        except Exception as e:
            if k == retries - 1:
                raise
            log(f"开流重试 {k+1}: {e}")
            time.sleep(1.0)


def normalize_numbers(text: str) -> str:
    """统一从 text_pipeline 导入（单一共享实现，合成/评分两侧一致）。"""
    from text_pipeline import normalize_numbers as _nn
    return _nn(text)


def split_sentences(text, max_len=60):
    """句级切分（。！？!?；;换行），过长句按逗号再切。"""
    parts = re.split(r"(?<=[。！？!?；;\n])", text.strip())
    out = []
    for p in (s.strip() for s in parts):
        if not p:
            continue
        if len(p) <= max_len:
            out.append(p)
            continue
        sub = re.split(r"(?<=[，,、：:])", p)
        cur = ""
        for s in sub:
            if cur and len(cur) + len(s) > max_len:
                out.append(cur)
                cur = s
            else:
                cur += s
        if cur:
            out.append(cur)
    return out


class Engine:
    """piper 引擎：加载一次 + 预热，稳态 RTF≈0.06。"""

    def __init__(self):
        name = CFG["engine"]["name"]
        t0 = time.perf_counter()
        if name == "moss":
            sys.path.insert(0, str(ROOT))
            from moss_engine import MossEngine, resolve_platform_threads
            self.tts = MossEngine(prompt_audio=CFG["engine"].get("prompt_audio", "assets/audio/zh_6.wav"),
                                  thread_count=resolve_platform_threads(CFG["engine"].get("threads", 4)))
            self.tts.synth("预热。")   # perf-20260922: 无标点预热会 AR 失控跑满帧上限（46.1s vs 4.1s 配对实测，HS-3）
            # 流式路径预热（pn-arm-firstframe-001）：codec streaming 内核首次执行 ~2-3s 冷启动，
            # 不暖机则落在首个真实请求上（实测首音 3.0s vs 热态 85ms）。
            if CFG["engine"].get("streaming_first_audio", True):
                for _chunk in self.tts.synth_streaming("暖机。"):
                    pass
        else:
            from mixed_tts import MixedTTS
            self.tts = MixedTTS(models_dir=ROOT / "models",
                                download_dir=ROOT / CFG["engine"]["download_dir"],
                                hf_endpoint=CFG["engine"].get("hf_endpoint"))
            self.tts.warmup()
        log(f"引擎[{name}]就绪（加载+预热 {time.perf_counter()-t0:.1f}s）")

    def synth(self, text):
        return self.tts.synth(text)

    def synth_streaming(self, text):
        return self.tts.synth_streaming(text)


def main():
    log("加载引擎...")
    engine = Engine()

    log("引擎就绪；输出流改为每请求按设备名新开（防拓扑变化句柄过期）")
    # 音量策略 v2：不碰系统音量。BlackHole 设备音量可能被系统重置到近零（-40dB），
    # 改用数字域自动增益补偿（启动校准 + 每句峰值限制），用户音量完全不受影响。

    def send_event(conn, ev: dict) -> None:
        """客户端断开只丢事件，绝不影响播放流水线。"""
        try:
            conn.sendall(json.dumps(ev).encode() + b"\n")
        except OSError:
            pass

    def calibrate_bh_gain(bh_stream):
        """播放校准音并从 BlackHole 输入端回采，自动计算增益补偿设备音量衰减。"""
        import numpy as _np
        bh_in = None
        for i in range(len(sd.query_devices())):
            d = sd.query_devices(i)
            if "blackhole" in d["name"].lower() and d["max_input_channels"] >= 2:
                bh_in = i; break
        if bh_in is None:
            return 1.0, 0.0
        buf = []
        sr = 48000
        st = sd.InputStream(device=bh_in, samplerate=sr, channels=2, dtype="int16",
                            blocksize=256, callback=lambda i, f, t_, s: buf.append(i.copy()))
        n = int(sr * 0.5)
        tt = _np.arange(n) / sr
        burst = (0.1 * _np.sin(2 * _np.pi * 1000 * tt) * 32767).astype(_np.int16)
        burst = _np.stack([burst, burst], axis=1)
        st.start()
        bh_stream.write(burst)
        time.sleep(0.7)
        st.stop(); st.close()
        if not buf:
            return 1.0, 0.0
        pcm = _np.concatenate(buf).astype(_np.float32).reshape(-1, 2).mean(axis=1) / 32768
        rms = float(_np.sqrt(_np.mean(pcm ** 2)))
        # 近零读数 ≠ 设备音量衰减（真实衰减特征是 rms≈0.001x）：多半是采集竞争
        # （sox/其他 App 占用输入端）或流启动时序漏采校准音，误补偿会压坏动态范围。
        if rms < 0.005:
            return 1.0, rms
        gain = max(1.0, min(40.0, 0.08 / max(rms, 1e-4)))
        return gain, rms

    def serve(conn):
        bh = open_output(CFG["device"]["name"])   # BlackHole 虚拟设备，按连接持有
        # monitor 每句重开（跟随系统默认输出，支持播放中切设备）
        sd.sleep(30)
        t_recv = time.perf_counter()
        buf = b""
        global BH_GAIN
        if BH_GAIN["v"] == 1.0:
            g, measured = calibrate_bh_gain(bh)
            BH_GAIN["v"] = g
            log(f"BlackHole 回环校准: 实测 RMS={measured:.4f} → 增益 ×{g:.1f}")
        send_event(conn, {"event": "ready"})
        while True:
            data = conn.recv(4096)
            if not data:
                return
            buf += data
            if b"\n" not in buf:
                continue
            line, buf = buf.split(b"\n", 1)
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = (req.get("text") or "").strip()
            if not text:
                continue
            if CFG["engine"]["name"] == "moss" and CFG["engine"].get("number_normalize", True):
                text = normalize_numbers(text)
            sentences = split_sentences(text)
            # P0 首音优化：首句在首个次级标点处再切分（≤12 字），首块音频更快出声。
            # 依据：first_audio ≈ 首句完整合成时间（实测占 99%），首句越短首音越快。
            if sentences and len(sentences[0]) > 12:
                import re as _re
                m = _re.search(r"^(.{2,12}?[，、：；,;])", sentences[0])   # perf-20260922: 4→2 字（HS-4：2字前缀"你好，"不切分是首音 8050ms 根因）
                if m and m.end() < len(sentences[0]):
                    sentences = [m.group(1)] + [sentences[0][m.end():]] + sentences[1:]
            synth_q = queue.Queue(maxsize=4)   # 有界队列 → 自然背压
            stats = {"synth": 0.0, "audio": 0.0, "first_audio": None}
            use_stream = bool(CFG["engine"].get("streaming_first_audio", True))

            def synth_worker():
                t_start = time.perf_counter()
                streamed = False
                for idx, s in enumerate(sentences):
                    if idx == 0 and use_stream:
                        try:
                            # 流式首句：AR 首帧生成即出块（首块 ~110ms），块级入队
                            for pcm, sr in engine.synth_streaming(s):
                                stats["audio"] += len(pcm) / sr
                                synth_q.put((pcm, sr))
                            streamed = True
                            continue
                        except Exception as e:
                            log(f"流式首句失败，回落整段合成: {e}")
                    t = time.perf_counter()
                    pcm, sr = engine.synth(s)
                    stats["synth"] += time.perf_counter() - t
                    stats["audio"] += len(pcm) / sr
                    synth_q.put((pcm, sr))
                if streamed:
                    stats["synth"] += time.perf_counter() - t_start
                synth_q.put(None)

            def feed(tag, stream, pcm, sr):
                try:
                    out = pcm
                    if tag == "bh" and BH_GAIN["v"] > 1.0:
                        f = pcm.astype(np.float32) * BH_GAIN["v"]
                        peak = np.abs(f).max()
                        if peak > 0.95 * 32768:
                            f = f / peak * 0.95 * 32768
                        out = f.astype(_np.int16)
                    stream.write(out)
                except Exception as e:
                    log(f"{tag} 写入失败: {e}")

            def play_worker():
                first = True
                while True:
                    item = synth_q.get()
                    if item is None:
                        break
                    pcm, sr = item
                    if first:
                        stats["first_audio"] = (time.perf_counter() - t_recv) * 1000
                        send_event(conn, {"event": "playback_started",
                                          "first_audio_ms": round(stats["first_audio"], 1)})
                        first = False
                    # monitor 同播：afplay 独立进程（跟随系统默认输出，零欠载）
                    mon_wav = f"/tmp/ttsd_mon_{int(time.perf_counter()*1000)}.wav"
                    with wave.open(mon_wav, "wb") as w:
                        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
                        w.writeframes(pcm.tobytes())
                    af = subprocess.Popen(["afplay", mon_wav],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    feed("bh", bh, pcm, sr)
                    try:
                        af.wait(timeout=60)
                        os.remove(mon_wav)
                    except Exception:
                        pass

            tw = threading.Thread(target=synth_worker); tw.start()
            play_worker()
            tw.join()
            send_event(conn, {"event": "done",
                              "audio_seconds": round(stats["audio"], 2),
                              "synth_seconds": round(stats["synth"], 2),
                              "sentences": len(sentences)})
            try:
                bh.stop(); bh.close()
                log("本请求输出流已关闭（monitor 为每句新开，无句柄过期问题）")
            except Exception:
                pass

    import fcntl
    lock_path = STATE_DIR / "ttsd.lock"
    lock_fp = open(lock_path, "w")
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("已有守护进程实例在运行（锁被持有），本次启动退出")
        sys.exit(0)
    if SOCK.exists():
        SOCK.unlink()
    # 首连接冷启动预热（pn-arm-firstframe-001）：AUHAL 首次开流 + 回环校准实测 ~2-3s，
    # 全部落在生命周期首个请求的客户端计时窗口内。提前到监听之前消化。
    try:
        _bh0 = open_output(CFG["device"]["name"])
        _g, _m = calibrate_bh_gain(_bh0)
        BH_GAIN["v"] = _g
        log(f"启动预热: BlackHole 首开 + 校准 RMS={_m:.4f} → 增益 ×{_g:.1f}")
        _bh0.stop(); _bh0.close()
    except Exception as e:
        log(f"启动预热失败（首个请求将承担冷启动）: {e}")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(SOCK))
    srv.listen(4)
    log(f"监听 {SOCK}")

    while True:
        conn, _ = srv.accept()
        log("客户端接入")
        threading.Thread(target=serve, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
