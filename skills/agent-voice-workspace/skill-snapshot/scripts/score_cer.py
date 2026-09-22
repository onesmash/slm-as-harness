#!/Users/xuhui/Code/research/research-output/tts-mic-loopback/deployment/.venv-moss/bin/python
"""score_cer.py — STT 转写 + 与原文对比 CER + 最差段报告。

用法:
  .venv-moss/bin/python score_cer.py <原文文件> <录音wav> <标签>
输出:
  /tmp/<标签>_asr.txt（转写） /tmp/<标签>_cer.json（报告）
"""
import json
import re
import sys
import time
from pathlib import Path

SRC = Path(sys.argv[1])
WAV = Path(sys.argv[2])
TAG = sys.argv[3] if len(sys.argv) > 3 else "iter"

MODEL_SIZE = sys.argv[4] if len(sys.argv) > 4 else "base"


from opencc import OpenCC
_CC = OpenCC("t2s")

def strip_hallucination_tail(text: str) -> str:
    """去掉 whisper 在尾部静音上的重复字符幻觉（嗯嗯嗯…/哈啊啊…）。"""
    return re.sub(r"([嗯啊呃嘛哦哈]{3,})\1+$", "", text.strip()).strip()

def zh_normalize(text: str, pinyin: bool = False) -> str:
    """CER/SER 对比用的归一化：数字→中文读法（cn2an，与 TTS 端一致）、繁→简、仅保留汉字；
    pinyin=True 时进一步转为无声调拼音序列（同音字不误伤，专测发音）。"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from text_pipeline import normalize_numbers
        text = normalize_numbers(text)
    except Exception:
        pass
    text = _CC.convert(text)
    text = "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    if pinyin:
        from pypinyin import lazy_pinyin, Style
        py = lazy_pinyin(text, style=Style.NORMAL, errors="ignore")
        return " ".join(py)
    return text


def edit_distance(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    if not ref:
        return 1.0
    return edit_distance(ref, hyp) / len(ref)


def align_worst(ref: str, hyp: str, window=30, top=5):
    """滑动窗口找 CER 最差的片段（定位发音问题）。"""
    outs = []
    step = max(10, window // 3)
    n = len(ref)
    for i in range(0, max(1, n - window), step):
        seg = ref[i:i+window]
        # 局部对齐：在 hyp 中取同比例区域附近搜索
        lo = max(0, int(i / n * len(hyp)) - 20)
        hi = min(len(hyp), int((i + window) / n * len(hyp)) + 20)
        seg_hyp = hyp[lo:hi]
        e = edit_distance(seg, seg_hyp)
        outs.append((e / window, i, seg, seg_hyp, e))
    outs.sort(reverse=True)
    seen, res = set(), []
    for r, i, seg, seg_hyp, e in outs:
        if any(abs(i - j) < window for j in seen):
            continue
        seen.add(i)
        res.append({"cer": round(r, 3), "pos": i, "ref": seg, "near_hyp": seg_hyp[:60]})
        if len(res) >= top:
            break
    return res


def main():
    src = SRC.read_text().strip()
    ref = zh_normalize(src)

    from faster_whisper import WhisperModel
    t0 = time.perf_counter()
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print(f"[cer] whisper-{MODEL_SIZE} 加载 {time.perf_counter()-t0:.1f}s", flush=True)

    t0 = time.perf_counter()
    segments, info = model.transcribe(str(WAV), language="zh", vad_filter=True,
                                      beam_size=1, condition_on_previous_text=False)
    hyp_parts = []
    for seg in segments:
        hyp_parts.append(seg.text.strip())
        print(f"  ASR [{seg.start:6.1f}s] {seg.text.strip()}", flush=True)
    hyp = strip_hallucination_tail("".join(hyp_parts))
    stt_s = time.perf_counter() - t0
    Path(f"/tmp/{TAG}_asr.txt").write_text(hyp)
    hyp_n = zh_normalize(hyp)

    c = cer(ref, hyp_n)
    ref_py = zh_normalize(src, pinyin=True)
    hyp_py = zh_normalize(hyp, pinyin=True)
    ser = cer(ref_py, hyp_py)
    print(f"[cer] 字级 CER={c:.3f} | 拼音级 SER={ser:.3f}（SER 扣除同音字误写，专测发音）"
          f" | STT 耗时 {stt_s:.0f}s", flush=True)

    worst = align_worst(ref, hyp_n)
    for w in worst:
        print(f"  差段@{w['pos']}: CER={w['cer']} 原文: {w['ref'][:30]}")

    report = {
        "tag": TAG, "model": MODEL_SIZE,
        "ref_chars": len(ref), "hyp_chars": len(hyp_n),
        "cer": round(c, 4),
        "pinyin_ser": round(ser, 4),
        "stt_seconds": round(stt_s, 1),
        "worst_segments": worst,
        "ref_normalized": ref,
        "hyp_normalized": hyp_n,
        "ref_pinyin": ref_py,
        "hyp_pinyin": hyp_py,
    }
    Path(f"/tmp/{TAG}_cer.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[cer] 报告 → /tmp/{TAG}_cer.json", flush=True)


if __name__ == "__main__":
    main()
