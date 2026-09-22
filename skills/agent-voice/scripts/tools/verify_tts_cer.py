#!/usr/bin/env python3
"""verify_tts_cer.py — MOSS 合成路径 CER 回归验证（STT 闭环）。

对句集分别用指定合成模式（整段 / 流式）产出音频，经 faster-whisper 转写后
与原文算字级 CER。用于合成路径改动（如 streaming 首帧优化）后的语义等价性
回归：两种模式的中位 CER 应逐句相同或差异极小。

用法:
  .venv-moss/bin/python tools/verify_tts_cer.py                      # 默认: nonstream vs stream 对比
  .venv-moss/bin/python tools/verify_tts_cer.py --modes stream      # 只测流式
  .venv-moss/bin/python tools/verify_tts_cer.py --repeats 5 --out r.json

依赖: pip 装 faster-whisper + opencc；模型 scripts/models/faster-whisper-base
（缺失时见 models/README.txt 从 hf-mirror 下载，或让其按 repo 名自动下载）。

判据: 对比模式下逐句要求两侧中位 CER 均 < 0.15 且 |差| < 0.10；
注意合成是采样模型（同模式重复合成 CER 亦波动），绝对水平受 ASR 噪声地板限制。
"""
import argparse
import json
import statistics
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parent.parent   # scripts/
sys.path.insert(0, str(SCRIPTS))

DEFAULT_SENTENCES = [
    "你好，世界。",
    "这是首帧延迟的测量语句，包含中间长度的内容。",
    "Apple Silicon 与 Intel 的核心拓扑差异显著，因此线程行为必须在目标平台上独立实测，不能跨平台复用结论。",
]
EQUIV_ABS = 0.15
EQUIV_DIFF = 0.10


def synth_to_wav(eng, text, mode, wav_path):
    """经生产引擎接口合成并写 48k 立体声 int16 WAV。"""
    if mode == "stream":
        chunks = []
        sr = 48000
        for pcm, sr in eng.synth_streaming(text):
            chunks.append(pcm)
        pcm = np.concatenate(chunks) if chunks else np.zeros((0, 2), np.int16)
    else:
        pcm, sr = eng.synth(text)
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return len(pcm) / sr


def main():
    ap = argparse.ArgumentParser(description="MOSS 合成 CER 回归验证")
    ap.add_argument("--modes", default="nonstream,stream",
                    help="逗号分隔: nonstream,stream（默认对比两者）")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--text-file", default=None, help="自定义句集（每行一句；默认内置 3 句）")
    ap.add_argument("--model-dir", default=None,
                    help="faster-whisper 模型目录（默认 scripts/models/faster-whisper-base，缺失则按名下载）")
    ap.add_argument("--out", default=None, help="JSON 报告输出路径")
    args = ap.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    unknown = [m for m in modes if m not in ("nonstream", "stream")]
    if unknown or not modes:
        sys.exit(f"[verify] --modes 仅支持 nonstream/stream，收到: {modes}")

    try:
        import faster_whisper  # noqa: F401
        import opencc  # noqa: F401
    except ModuleNotFoundError as e:
        sys.exit(f"[verify] 缺依赖: {e.name}（.venv-moss/bin/pip install faster-whisper opencc）")

    sentences = ([ln.strip() for ln in Path(args.text_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
                 if args.text_file else DEFAULT_SENTENCES)

    import os
    os.chdir(SCRIPTS)
    from moss_engine import MossEngine, resolve_platform_threads
    from config_loader import load_config
    cfg, _ = load_config()
    eng = MossEngine(prompt_audio=cfg["engine"].get("prompt_audio", "assets/audio/zh_6.wav"),
                     thread_count=resolve_platform_threads(cfg["engine"].get("threads", 4)))
    eng.synth("预热。")
    if "stream" in modes:
        for _ in eng.synth_streaming("暖机。"):
            pass   # 流式 kernel 冷启动排除在测量外

    model_dir = args.model_dir or str(SCRIPTS / "models" / "faster-whisper-base")
    model_ref = model_dir if Path(model_dir).exists() else "base"
    from faster_whisper import WhisperModel
    t0 = time.perf_counter()
    wm = WhisperModel(model_ref, device="cpu", compute_type="int8")
    print(f"[verify] whisper 加载自 {model_ref}（{time.perf_counter()-t0:.1f}s）", flush=True)

    from text_pipeline import normalize_numbers as _nn
    from opencc import OpenCC as _OpenCC
    _CC = _OpenCC("t2s")

    def strip_hallucination_tail(text):
        import re
        return re.sub(r"([嗯啊呃嘛哦哈]{3,})\1+$", "", text.strip()).strip()

    def zh_normalize(text):
        try:
            text = _nn(text)
        except Exception:
            pass
        text = _CC.convert(text)
        return "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")

    def edit_distance(a, b):
        if len(a) < len(b):
            a, b = b, a
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1], prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]

    def cer(ref, hyp):
        return edit_distance(ref, hyp) / len(ref) if ref else 1.0

    def transcribe(wav):
        segments, _ = wm.transcribe(wav, language="zh", vad_filter=True,
                                    beam_size=1, condition_on_previous_text=False)
        return strip_hallucination_tail("".join(s.text.strip() for s in segments))

    rows, verdict = [], []
    for si, text in enumerate(sentences):
        ref = zh_normalize(text)
        cers = {m: [] for m in modes}
        for rep in range(args.repeats):
            for mode in modes:
                wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                dur = synth_to_wav(eng, text, mode, wav)
                c = cer(ref, zh_normalize(transcribe(wav)))
                cers[mode].append(c)
                Path(wav).unlink(missing_ok=True)
                print(f"s{si} rep{rep+1} {mode}: CER={c:.3f} dur={dur:.2f}s", flush=True)
        row = {"sentence_idx": si, "chars": len(text),
               "cer": {m: [round(c, 4) for c in cers[m]] for m in modes},
               "cer_median": {m: round(statistics.median(cers[m]), 4) for m in modes}}
        rows.append(row)
        print(f"--> s{si}: {row['cer_median']}", flush=True)

    if set(modes) == {"nonstream", "stream"}:
        for row in rows:
            a, b = row["cer_median"]["nonstream"], row["cer_median"]["stream"]
            row["equivalent"] = bool(a < EQUIV_ABS and b < EQUIV_ABS and abs(b - a) < EQUIV_DIFF)
        equivalent_all = all(r["equivalent"] for r in rows)
    else:
        equivalent_all = None

    summary = {
        "modes": modes, "repeats": args.repeats, "sentences": len(sentences),
        "rows": rows, "equivalent_all": equivalent_all,
        "rule": f"对比模式逐句中位: 双方 < {EQUIV_ABS} 且 |差| < {EQUIV_DIFF}；绝对水平受 ASR 噪声地板限制",
    }
    out_path = Path(args.out) if args.out else Path(__file__).resolve().parent / "verify_tts_cer_report.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
