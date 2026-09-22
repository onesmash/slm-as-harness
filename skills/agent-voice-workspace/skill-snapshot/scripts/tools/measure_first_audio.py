#!/usr/bin/env python3
"""measure_first_audio.py — BlackHole 回环延迟实测（playrec 同流双标记差分）。

原理：用 sd.playrec 在「同一 PortAudio 流」里同时播放+采集（输入输出样本严格对齐），
输出信号 = 前导静音(0.3s) + 50ms 1kHz 标记 burst + 尾静音；录制中用互相关定位
burst 实际到达样本，与理论位置之差即全环路延迟（输出缓冲→BlackHole→输入采集）。

用法:
    measure_first_audio.py --blocksize 256 --runs 3 --json out.json

输出 JSON: {blocksize, runs, p50_ms, p95_ms, excess_ms, samples:[...]}
    excess_ms = p50 − 单缓冲周期(bs/SR)，衡量超出一个缓冲周期的额外环路延迟。
"""
import argparse
import json
import statistics
import time

import numpy as np
import sounddevice as sd

SR = 48000
LEAD_S = 0.3
BURST_S = 0.05
TAIL_S = 0.3


def find_devices():
    dev_out = dev_in = None
    for i in range(len(sd.query_devices())):
        d = sd.query_devices(i)
        n = d["name"].lower()
        if "blackhole" not in n:
            continue
        if d["max_output_channels"] >= 2 and dev_out is None:
            dev_out = i
        if d["max_input_channels"] >= 2 and dev_in is None:
            dev_in = i
    return dev_out, dev_in


def measure_once(dev_out, dev_in, blocksize):
    lead, n_burst, tail = (int(SR * LEAD_S), int(SR * BURST_S), int(SR * TAIL_S))
    t = np.arange(n_burst) / SR
    burst = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    out_sig = np.zeros((lead + n_burst + tail, 2), dtype=np.int16)
    out_sig[lead:lead + n_burst, 0] = (burst * 32767 * 0.9).astype(np.int16)
    out_sig[lead:lead + n_burst, 1] = out_sig[lead:lead + n_burst, 0]

    rec = sd.playrec(out_sig, samplerate=SR, channels=2, dtype="int16",
                     device=(dev_in, dev_out), blocksize=blocksize,
                     latency="low", blocking=True)
    mono = rec.astype(np.float32).mean(axis=1) / 32768

    # 互相关定位 burst 到达位置（只在前导+突发附近窗口搜索，省时）
    win = mono[max(0, lead - int(SR * 0.05)): lead + n_burst + int(SR * 0.1)]
    corr = np.correlate(win - win.mean(), burst - burst.mean(), mode="valid")
    peak_rel = int(np.argmax(np.abs(corr)))
    idx_arr = peak_rel + max(0, lead - int(SR * 0.05))
    latency_ms = (idx_arr - lead) / SR * 1000.0
    peak = float(np.max(np.abs(corr)))
    if peak < 1.0:
        raise RuntimeError(f"回环信号太弱（corr peak={peak:.2f}）")
    return round(latency_ms, 3), peak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocksize", type=int, default=256)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--json", dest="json_path", default=None)
    args = ap.parse_args()

    dev_out, dev_in = find_devices()
    if dev_out is None or dev_in is None:
        print(json.dumps({"error": "BlackHole 设备未找到"}))
        raise SystemExit(2)

    samples = []
    for r in range(args.runs):
        try:
            ms, peak = measure_once(dev_out, dev_in, args.blocksize)
            samples.append(ms)
            print(f"[run {r + 1}/{args.runs}] bs={args.blocksize} "
                  f"loop={ms:.2f}ms (xcorr peak={peak:.0f})", flush=True)
        except Exception as e:
            print(f"[run {r + 1}/{args.runs}] FAIL: {e}", flush=True)
        time.sleep(0.2)

    result = {"blocksize": args.blocksize, "runs": args.runs}
    if samples:
        s = sorted(samples)
        result["samples_ms"] = s
        result["p50_ms"] = round(statistics.median(s), 3)
        result["p95_ms"] = round(s[min(len(s) - 1, int(round(0.95 * len(s) + 0.5)) - 1)], 3)
        result["excess_ms"] = round(result["p50_ms"] - args.blocksize / SR * 1000.0, 3)
        result["ok"] = True
    else:
        result["ok"] = False
        result["error"] = "所有 run 均失败"
    print(json.dumps(result, ensure_ascii=False))
    if args.json_path:
        with open(args.json_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
