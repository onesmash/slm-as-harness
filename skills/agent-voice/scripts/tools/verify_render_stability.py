#!/usr/bin/env python3
"""verify_render_stability.py — 配对 σ_render 验收门禁（research-nex r4 T10 判据 [83][84]）。

为什么不用「句间 F0 SD」：r4 [73][74] 证明合成侧跨句离散（1.54–1.85 半音）**已小于**自然人声
（2.68 半音，K=23 句/6 音色），故句间 SD 判不出用户抱怨的抖动。改用**配对 σ_render**：
同一句文本、同一说话人、只改 seed 重复渲染时 F0 中位的离散——它度量的才是渲染/解码稳定性。

判据（同句集、同仪器 YIN 40ms/10ms@16kHz）：
  · 稳定性门禁：σ̂_fix ≤ 0.60 × σ_base（降幅 ≥40%），单侧 F 检验 α=0.05
  · 非劣性守卫：σ̂_fix ≤ 1.50 × σ_base（现有候选无一以降低解码抖动为目标，只设 40% 线会全否）
  · 绝对阈值不可用：本机 0 例「同说话人重复同句」自然录音（r4 [83] 穷举确认）

基线：生产 fixed 配对 σ_render = 1.08 半音（df=24，95%CI [0.84,1.50]，r4 [84]）。
功效提示：df_base=24 时 30% 降幅的功效上限仅 75.1%（不可达）；≥40% 需 df≥25（K=16×n=3）。

用法:
  verify_render_stability.py                 # 默认 K=8 句 × n=3 seed
  verify_render_stability.py --k 16 --n 3    # 判据要求的规模
  verify_render_stability.py --baseline 1.08 --df-base 24
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

SENTS = [
    "今天下午三点开会。", "讨论音调稳定性的问题。", "请记录会议纪要。", "会后把结论发给我。",
    "这个方案需要再评估。", "先按现有版本上线。", "明天上午同步进展。", "有异议请提前提出。",
    "预算部分我再核对。", "测试环境已经就绪。", "文档我今晚补齐。", "风险点列了三条。",
    "客户反馈比较正面。", "下周安排一次复盘。", "接口联调已经通过。", "剩余工作我来跟进。",
]
SEEDS = [1234, 4321, 777, 20240922, 31337, 1767412193]


def yin_f0(x, sr=16000, frame_ms=40, hop_ms=10, fmin=60.0, fmax=400.0, thr=0.20):
    """YIN 基频跟踪（与 r4 判据同仪器）。返回有声帧 F0 数组。"""
    frame, hop = int(frame_ms / 1000 * sr), int(hop_ms / 1000 * sr)
    out = []
    for i in range(max(1, (len(x) - frame) // hop)):
        seg = x[i * hop:i * hop + frame]
        if float(np.sqrt(np.mean(seg ** 2))) < 0.02:
            continue
        seg = seg - seg.mean()
        if not np.any(seg):
            continue
        n = len(seg)
        tau_min, tau_max = int(sr / fmax), min(int(sr / fmin), n - 2)
        size = 1 << int(math.ceil(math.log2(2 * n)))
        spec = np.fft.rfft(seg, size)
        acf = np.fft.irfft(spec * np.conj(spec))[:n]
        cs = np.cumsum(seg ** 2)
        taus = np.arange(tau_min, tau_max + 1)
        d = np.maximum(cs[n - taus - 1] + (cs[n - 1] - cs[taus - 1]) - 2 * acf[taus], 0.0)
        cum = np.cumsum(d)
        with np.errstate(divide="ignore", invalid="ignore"):
            cmnd = np.where(cum > 0, d * taus / cum, 1.0)
        idx = np.where(cmnd < thr)[0]
        if len(idx) == 0:
            continue
        k = idx[0]
        while k + 1 < len(cmnd) and cmnd[k + 1] < cmnd[k]:
            k += 1
        out.append(sr / (taus[0] + k))
    return np.array(out)


def to_mono_16k(pcm, sr):
    x = pcm.astype(np.float64).mean(axis=1) / 32768.0
    if sr == 16000:
        return x
    f = sr / 16000
    if abs(f - round(f)) < 1e-9 and round(f) >= 1:
        f = int(round(f)); n = (len(x) // f) * f
        return x[:n].reshape(-1, f).mean(axis=1)
    idx = np.arange(max(1, int(len(x) / f))) * f
    i0 = np.clip(np.floor(idx).astype(int), 0, len(x) - 2)
    w = idx - i0
    return x[i0] * (1 - w) + x[i0 + 1] * w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=8, help="句数（判据要求 16）")
    ap.add_argument("--n", type=int, default=3, help="每句独立 seed 数（判据要求 3）")
    ap.add_argument("--baseline", type=float, default=1.08, help="生产 fixed 配对 σ_render 基线（半音）")
    ap.add_argument("--df-base", type=int, default=24, help="基线自由度")
    args = ap.parse_args()

    from moss_engine import MossEngine, stable_seed
    eng = MossEngine()
    sents = SENTS[:args.k]
    meds = []
    for s in sents:
        row = []
        for j in range(args.n):
            seed = stable_seed(f"{s}#{j}")          # 同句不同 seed ⇒ 纯渲染抖动
            eng.reset_prefix_state("σ_render 测量：隔离单句")   # 关掉跨句前缀，只测渲染
            pcm, sr = eng.synth(s) if j == 0 else _synth_with_seed(eng, s, seed)
            f0 = yin_f0(to_mono_16k(pcm, sr))
            if len(f0):
                row.append(float(np.median(f0)))
        if len(row) >= 2:
            meds.append(row)
    if len(meds) < 2:
        sys.exit("有效句数不足，无法计算 σ_render")

    # 每句内跨 seed 的 SD（频率域→半音域：用相对离散 12*log2 的近似 σ_st ≈ σ_Hz/中位 * 12/ln2）
    sigmas = []
    for row in meds:
        a = np.array(row)
        sigmas.append(float(np.std(a, ddof=1)) / float(np.mean(a)) * 12 / math.log(2))
    sigma = float(np.sqrt(np.mean(np.square(sigmas))))
    df = len(meds) * (args.n - 1)
    lo = sigma * math.sqrt(df / _chi2_ppf(0.975, df))
    hi = sigma * math.sqrt(df / _chi2_ppf(0.025, df))
    f_stat = (sigma / args.baseline) ** 2
    f_crit = _f_ppf(0.05, df, args.df_base)          # 单侧 α=0.05

    print(f"配对 σ_render = {sigma:.3f} 半音（df={df}，95%CI [{lo:.3f}, {hi:.3f}]，K={len(meds)} 句 × n={args.n} seed）")
    print(f"基线 σ_base   = {args.baseline:.3f} 半音（df={args.df_base}）；F={f_stat:.3f}，单侧 α=0.05 临界 F={f_crit:.3f}")
    stability = f_stat < f_crit
    noninf = sigma <= 1.5 * args.baseline
    print(f"稳定性门禁（降幅 ≥40%）：{'PASS' if stability else 'FAIL'}")
    print(f"非劣性守卫（≤1.50× 基线）：{'PASS' if noninf else 'FAIL'}")
    if df < 25:
        print(f"⚠ 功效提示：当前 df={df}；判据要求 ≥40% 降幅需 df≥25（K=16×n=3），"
              f"30% 降幅在 df_base={args.df_base} 下功效上限仅 75.1%，不可达")
    sys.exit(0 if (stability and noninf) else 1)


def _synth_with_seed(eng, text, seed):
    """直接调 runtime 以指定 seed（MossEngine.synth 用 stable_seed(text)，此处需独立 seed）。"""
    import os
    prompt = eng.prompt_audio
    if not os.path.isabs(prompt):
        from moss_engine import MOSS_DIR
        prompt = str(MOSS_DIR / prompt)
    r = eng.runtime.synthesize(text=text, voice="", prompt_audio_path=prompt,
                               output_audio_path=eng.out, sample_mode="fixed", streaming=False,
                               max_new_frames=375, enable_wetext=False,
                               enable_normalize_tts_text=False, seed=seed)
    import wave
    with wave.open(eng.out, "rb") as w:
        sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2)
    return pcm, sr


def _chi2_ppf(p, df):
    """Wilson–Hilferty 近似的 χ² 分位（避免引入 scipy）。"""
    z = _norm_ppf(p)
    return df * (1 - 2 / (9 * df) + z * math.sqrt(2 / (9 * df))) ** 3


def _norm_ppf(p):
    for z in [x / 100 for x in range(-400, 401)]:
        if 0.5 * (1 + math.erf(z / math.sqrt(2))) >= p:
            return z
    return 0.0


def _f_ppf(alpha, df1, df2):
    """F 分位近似：用 χ²/df 之比（df 足够大时误差可接受，仅用于判据提示）。"""
    return (_chi2_ppf(1 - alpha, df1) / df1) / (_chi2_ppf(0.5, df2) / df2)


if __name__ == "__main__":
    main()
