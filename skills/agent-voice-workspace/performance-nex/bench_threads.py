#!/usr/bin/env python3
"""bench_threads.py — ARM 平台 ORT intra_op 线程数单变量扫描（performance-nex PN 任务）。

契约（benchmark_plan.json）:
- 工作负载: 5 句固定句集 × 3 repeats，每配置预热 1 句后计时
- 指标: per-request synth_seconds / audio_seconds / RTF
- 正确性: 每句输出 int16 PCM 与 threads=4 基线 bit-exact（sha256 比对）
- 单变量: 仅 thread_count 变化；模型/prompt/sample_mode 全部固定
"""
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
import wave
from pathlib import Path

SCRIPTS = Path("/Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts")
sys.path.insert(0, str(SCRIPTS))

SENTENCES = [
    "你好，世界。",
    "这是苹果芯片平台的合成测试。",
    "数字归一化检查：12306 次列车准点到达。",
    "performance-nex 要求先建立基线再做单变量假设轮换，同负载重测并保留正确性证据。",
    "Apple Silicon 与 Intel 的核心拓扑差异显著：性能核与能效核的异构调度会改变 ONNX Runtime 线程池的行为，因此线程数必须在目标平台上独立实测，不能跨平台复用结论。",
]
REPEATS = 3
CONFIGS = [1, 2, 4, 6, 8, 12]
BASELINE = 4
OUT_DIR = Path(__file__).resolve().parent


def synth_once(engine, text):
    t0 = time.perf_counter()
    pcm, sr = engine.synth(text)
    dt = time.perf_counter() - t0
    audio = len(pcm) / sr
    return dt, audio, pcm.tobytes(), sr


def run_config(threads):
    from moss_engine import MossEngine
    t_load = time.perf_counter()
    eng = MossEngine(prompt_audio="assets/audio/zh_6.wav", thread_count=threads)
    load_s = time.perf_counter() - t_load
    eng.synth("预热。")  # warmup（不计入）
    rows = []
    for rep in range(REPEATS):
        for si, text in enumerate(SENTENCES):
            dt, audio, raw, sr = synth_once(eng, text)
            rows.append({
                "threads": threads, "rep": rep, "sentence_idx": si,
                "synth_seconds": round(dt, 4), "audio_seconds": round(audio, 4),
                "rtf": round(dt / audio, 4),
                "pcm_sha256": hashlib.sha256(raw).hexdigest(),
                "pcm_bytes": len(raw),
            })
            print(f"  t={threads} rep{rep + 1} s{si + 1}: synth={dt:.3f}s audio={audio:.2f}s rtf={dt / audio:.3f}", flush=True)
    return {"threads": threads, "load_seconds": round(load_s, 2), "rows": rows}


def main():
    assert platform.machine() == "arm64", "本 harness 仅在 ARM 平台执行（平台隔离）"
    results = []
    for t in CONFIGS:
        print(f"[config] intra_op_num_threads={t}", flush=True)
        results.append(run_config(t))

    # 正确性：以基线配置的 sha256 为参照
    base = next(r for r in results if r["threads"] == BASELINE)
    base_map = {(r["sentence_idx"], r["rep"]): r["pcm_sha256"] for r in base["rows"]}
    correctness = {"bit_exact_policy": "sha256(int16 pcm) == baseline(t=4)", "per_config": {}}
    for r in results:
        mism = [k for k, v in (( (x["sentence_idx"], x["rep"]), x["pcm_sha256"]) for x in r["rows"]) if base_map[k] != v]
        correctness["per_config"][str(r["threads"])] = {
            "bit_exact": not mism, "mismatch_count": len(mism), "total": len(r["rows"])}

    # 统计
    stats = {}
    for r in results:
        rtfs = [x["rtf"] for x in r["rows"]]
        syn = sorted(x["synth_seconds"] for x in r["rows"])
        n = len(rtfs)
        p95 = syn[min(n - 1, int(round(0.95 * n + 0.5)) - 1)]
        cv = statistics.stdev(rtfs) / statistics.mean(rtfs) if n > 1 else 0.0
        stats[str(r["threads"])] = {
            "rtf_median": round(statistics.median(rtfs), 4),
            "rtf_mean": round(statistics.mean(rtfs), 4),
            "rtf_cv": round(cv, 4),
            "synth_p50_s": round(statistics.median(syn), 4),
            "synth_p95_s": round(p95, 4),
        }

    base_median = stats[str(BASELINE)]["rtf_median"]
    base_cv = stats[str(BASELINE)]["rtf_cv"]
    verdict = {}
    for t, s in stats.items():
        delta = (s["rtf_median"] - base_median) / base_median
        sig = abs(delta) > 2 * base_cv
        verdict[str(t)] = {
            "rtf_delta_vs_baseline": round(delta, 4),
            "significant": bool(sig),
            "beats_baseline": bool(sig and delta < 0),
            "bit_exact": correctness["per_config"][t]["bit_exact"],
        }

    out = {
        "run_id": "pn-arm-threads-001",
        "machine": platform.machine(),
        "chip": subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                               capture_output=True, text=True).stdout.strip(),
        "results": results, "stats": stats, "correctness": correctness, "verdict": verdict,
        "baseline_threads": BASELINE,
    }
    (OUT_DIR / "benchmark_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))

    print("\n=== SUMMARY ===", flush=True)
    for t in CONFIGS:
        s, v = stats[str(t)], verdict[str(t)]
        print(f"t={t:>2}: rtf_med={s['rtf_median']:.4f} cv={s['rtf_cv']:.3f} "
              f"delta={v['rtf_delta_vs_baseline']:+.1%} sig={v['significant']} "
              f"bit_exact={v['bit_exact']}")


if __name__ == "__main__":
    main()
