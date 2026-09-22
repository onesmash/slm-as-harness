#!/usr/bin/env python3
"""selftest.py — 部署自测（T1–T5），对应 report.md 部署期验证清单。

T1 离线合成       say → WAV 有效（采样率/时长/非静音）
T2 输出通路       sounddevice 写 BlackHole 输出端无异常
T3 输入通路       从 BlackHole 输入端采集（触发 TCC 门禁，挂起=待授权）
T4 端到端回环     同时播放+采集，互相关验证信号到达
T5 延迟实测       playrec 同流互相关 3 档 blocksize × 3 run，回填 P50/P95

结果写入 selftest_report.json；任何失败 fail-closed 并给出修复指引。
"""
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

HERE = Path(__file__).resolve().parent
PY = str(Path(sys.executable))
REPORT = {"started": time.strftime("%Y-%m-%dT%H:%M:%S"), "tests": {}}
SR = 48000


def bh_devices():
    """返回 (输出设备id, 输入设备id)；统一从 text_pipeline 导入。"""
    from text_pipeline import find_bh_output, find_bh_input
    return find_bh_output(), find_bh_input()


def check(name, ok, detail, **extra):
    REPORT["tests"][name] = {"ok": bool(ok), "detail": detail, **extra}
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return bool(ok)


def t1_synthesis():
    wav = HERE / "_t1.wav"
    r = subprocess.run(["say", "-v", "Tingting", "-o", str(wav),
                        "--data-format", "LEI16@48000", "部署自测，本地离线合成。"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return check("T1_synthesis", False, f"say 退出码 {r.returncode}: {r.stderr[:120]}")
    with wave.open(str(wav), "rb") as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        pcm = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    wav.unlink()
    rms = float(np.sqrt(np.mean(pcm ** 2)))
    return check("T1_synthesis", n > 0 and sr == SR and rms > 0.01,
                 f"sr={sr} ch={ch} 时长={n/sr:.2f}s RMS={rms:.3f}",
                 samplerate=sr, seconds=n / sr, rms=rms)


def t2_playback(dev_out):
    """向 BlackHole 输出端写 0.5s 正弦，无异常且无欠载即过。"""
    t = np.arange(int(SR * 0.5)) / SR
    tone = (0.2 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    tone = np.stack([tone, tone], axis=1)
    try:
        st = sd.OutputStream(device=dev_out, samplerate=SR, channels=2,
                             dtype="int16", blocksize=256, latency="low")
        st.start()
        st.write(tone)
        st.stop()
        st.close()
        return check("T2_playback", True, f"0.5s/440Hz 写入 device#{dev_out} 成功，无异常")
    except Exception as e:
        return check("T2_playback", False, f"播放异常: {e}")


def t3_capture(dev_in):
    """从 BlackHole 输入端开流采集 0.5s；TCC 挂起会被超时截断并标记待授权。"""
    got = {"frames": None, "err": None}

    def cb(indata, frames, t, status):
        if got["frames"] is None:
            got["frames"] = (indata.copy(), status)

    def open_stream():
        st = sd.InputStream(device=dev_in, samplerate=SR, channels=2,
                            dtype="int16", blocksize=256, latency="low", callback=cb)
        st.start()
        return st

    import threading
    result = {}

    def runner():
        try:
            st = open_stream()
            time.sleep(0.6)
            st.stop()
            st.close()
            result["st"] = True
        except Exception as e:
            result["err"] = str(e)

    th = threading.Thread(target=runner, daemon=True)
    th.start()
    th.join(timeout=8)   # TCC 挂起时 start() 不返回
    if th.is_alive():
        return check("T3_capture", False,
                     "InputStream 启动挂起 >8s —— 几乎确定为 TCC 麦克风授权弹窗待批准。"
                     "请在 系统设置→隐私与安全性→麦克风 中为宿主 App（Terminal/iTerm）授权后重跑",
                     tcc_blocked=True)
    if result.get("err"):
        return check("T3_capture", False, f"采集异常: {result['err']}")
    frames, status = got["frames"]
    rms = float(np.sqrt(np.mean((frames.astype(np.float32) / 32768) ** 2)))
    flags = str(status) if status else "none"
    return check("T3_capture", True, f"0.6s 采集成功 RMS={rms:.5f} callback_status={flags}",
                 rms=rms, callback_status=flags)


def t4_loopback(dev_out, dev_in, seconds=2.5):
    """播放线性调频信号到 BlackHole，同时采集，互相关验证信号到达。"""
    import threading
    rec = {"buf": [], "err": None}

    def cin(indata, frames, t, status):
        rec["buf"].append(indata.copy())

    t = np.arange(int(SR * 1.0)) / SR
    chirp = (0.25 * np.sin(2 * np.pi * (800 + 2400 * t / 1.0) * t) * 32767).astype(np.int16)
    chirp = np.stack([chirp, chirp], axis=1)

    st_in = sd.InputStream(device=dev_in, samplerate=SR, channels=2,
                           dtype="int16", blocksize=256, latency="low", callback=cin)
    st_out = sd.OutputStream(device=dev_out, samplerate=SR, channels=2,
                             dtype="int16", blocksize=256, latency="low")

    def run():
        try:
            st_in.start(); time.sleep(0.3)
            st_out.start()
            st_out.write(chirp)          # 播放 1.0s chirp
            time.sleep(seconds - 1.3)    # 留出余量
            st_out.stop()
            st_in.stop()
            st_in.close()
            rec["ok"] = True
        except Exception as e:
            rec["err"] = str(e)

    th = threading.Thread(target=run, daemon=True)
    th.start()
    th.join(timeout=seconds + 10)
    if th.is_alive():
        return check("T4_loopback", False, "回环线程挂起（TCC 待授权？）", tcc_blocked=True)
    if rec.get("err"):
        return check("T4_loopback", False, f"回环异常: {rec['err']}")
    data = np.concatenate(rec["buf"]).astype(np.float32) / 32768
    mono = data.mean(axis=1)
    # 与理想 chirp 互相关
    ref = (0.25 * np.sin(2 * np.pi * (800 + 2400 * t / 1.0) * t)).astype(np.float32)
    corr = np.correlate(mono - mono.mean(), ref - ref.mean(), mode="valid")
    peak = float(np.max(np.abs(corr)))
    rms = float(np.sqrt(np.mean(mono ** 2)))
    matched = peak > 0.05 * len(ref) * (rms + 1e-9)
    return check("T4_loopback", matched,
                 f"录制 {len(mono)/SR:.2f}s RMS={rms:.4f} 互相关峰值={peak:.1f} "
                 f"({'检测到回环信号' if matched else '未检测到信号——检查设备选择'})",
                 rms=rms, xcorr_peak=peak)


def t5_verdict(results, sr=48000):
    """T5 数值判定（fail-closed）：不只看探针是否产出，还要求数值物理自洽。

    同流全双工回环延迟恒为 blocksize 的整数倍缓冲周期（见 tools/measure_first_audio.py 口径），
    故判据：① 三档都有数值 p50_ms；② 0 < p50 ≤ 200ms；③ p50 ≈ 缓冲周期整数倍；
    ④ 同档重复测量极差 ≤ 1ms（不稳定即视为测量无效）；⑤ p50 随 blocksize 单调不降。
    返回失败原因列表；空列表 = 通过。
    """
    bad = []
    for bs in (256, 512, 1024):
        v = results.get(bs)
        if not isinstance(v, dict) or "p50_ms" not in v:
            bad.append(f"bs{bs} 无 p50_ms（探针未产出）")
            continue
        try:
            p50 = float(v["p50_ms"])
        except (TypeError, ValueError):
            bad.append(f"bs{bs} p50_ms 非数值: {v['p50_ms']!r}")
            continue
        if not 0 < p50 <= 200:
            bad.append(f"bs{bs} p50={p50}ms 超出合理区间 (0,200]")
        period = bs / sr * 1000.0
        k = p50 / period
        if k < 1 or abs(k - round(k)) > 0.05:
            bad.append(f"bs{bs} p50={p50}ms 非缓冲周期整数倍（k={k:.3f}，周期={period:.3f}ms）")
        samples = v.get("samples")
        if isinstance(samples, list) and len(samples) >= 2:
            spread = max(samples) - min(samples)
            if spread > 1.0:
                bad.append(f"bs{bs} 重复测量极差 {spread:.2f}ms > 1ms（不稳定）")
    p50s = [float(results[bs]["p50_ms"]) for bs in (256, 512, 1024)
            if isinstance(results.get(bs), dict)
            and isinstance(results[bs].get("p50_ms"), (int, float))]
    if len(p50s) == 3 and not (p50s[0] <= p50s[1] <= p50s[2]):
        bad.append(f"p50 随 blocksize 非单调不降: {p50s}")
    return bad


def t5_latency(dev_out, dev_in):
    """调用同流 playrec 互相关脚本 3 档 blocksize × 3 run。"""
    script = HERE / "tools" / "measure_first_audio.py"
    if not script.exists():
        return check("T5_latency", False, f"测量脚本不存在: {script}")
    results = {}
    for bs in (256, 512, 1024):
        out_json = HERE / f"_t5_bs{bs}.json"
        r = subprocess.run([PY, str(script), "--blocksize", str(bs), "--runs", "3",
                            "--json", str(out_json)],
                           capture_output=True, text=True, timeout=180, cwd=str(HERE))
        data = None
        if out_json.exists():
            try:
                data = json.loads(out_json.read_text())
            except Exception:
                data = None
        results[bs] = data if data is not None else {"raw": r.stdout[-200:], "stderr": r.stderr[-200:]}
    reasons = t5_verdict(results)
    detail = "3 档实测完成: " + ", ".join(f"bs{b}={json.dumps(v)[:80]}" for b, v in results.items())
    if reasons:
        detail += "；判定失败: " + "; ".join(reasons)
    return check("T5_latency", not reasons, detail, measurements=results)


def main():
    dev_out, dev_in = bh_devices()
    if dev_out is None:
        print("FAIL: 未找到 BlackHole 设备——请确认安装与 coreaudiod 已重启")
        REPORT["tests"]["device"] = {"ok": False, "detail": "BlackHole 未注册"}
    else:
        REPORT["tests"]["device"] = {"ok": True, "detail": f"out=#{dev_out} in=#{dev_in}"}
        print(f"[ OK ] device: BlackHole out=#{dev_out} in=#{dev_in}")
        t1_synthesis()
        if not t2_playback(dev_out):
            pass
        if dev_in is not None:
            if t3_capture(dev_in):
                t4_loopback(dev_out, dev_in)
                t5_latency(dev_out, dev_in)
            else:
                print("[SKIP] T4/T5 依赖 T3 输入通路")
        else:
            print("[SKIP] T3/T4/T5：BlackHole 输入端口未枚举")
    ok_all = all(t.get("ok") for t in REPORT["tests"].values()) and REPORT["tests"]
    REPORT["overall"] = "pass" if ok_all else "fail"
    here = HERE / "selftest_report.json"
    here.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2))
    print(f"\noverall={REPORT['overall']} → {here}")


if __name__ == "__main__":
    main()
