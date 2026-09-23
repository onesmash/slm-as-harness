#!/usr/bin/env python3
"""moss_engine.py — MOSS-TTS-Nano ONNX 引擎适配器（质量档，单声音原生中英混读）。

依赖：.venv-moss（py3.12 + onnxruntime + torch2.2.2 + transformers）+ MOSS-TTS-Nano 仓库文件
许可：Apache-2.0
注意：MOSS 为自回归模型，本机（Intel CPU）RTF≈0.6-1.3；threads=4 实测最优（perf-20260922，ORT 1.23.2）。
接口与其他引擎一致：synth(text) -> (48k 立体声 int16, sr)
"""
import logging
import os
import platform
import sys
import time
import threading
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent          # scripts/
BASE = ROOT.parent                               # tts-mic-loopback/
MOSS_DIR = ROOT / "MOSS-TTS-Nano"

# ---- 跑飞守卫（cross-sentence-consistency 研究 [143][144][151]）----
# 背景：生产路径实测「帧数/字数」比稳定在 1.89–4.62；而短单元（≤3 字）与符号块会出现
# 125–187.5 帧/字的量级（2 字「在吗」→ 375 帧=30.00s），即模型不终止并撞满 max_new_frames。
# 判据 `帧数 > 帧/字比 × 字数 + 常数`；命中即换一个 seed 重渲（不改变正常渲染的读法）。
RUNAWAY_FRAMES_PER_CHAR = 5.0        # 生产最大实测 4.62；取 5.0 留 8% 余量，且不误伤 32 字短切单元（实测 188 帧 < 220 上限）
RUNAWAY_FRAME_BUFFER = 60            # 绝对余量，避免短文本触发过紧
RUNAWAY_MAX_RETRIES = 1              # 重试次数上限（=1 时单句最多 2 次合成）
RUNAWAY_HARD_CAP_MULTIPLIER = 4      # 截断上限 = 4× 检测上限（生产最大比 4.62 ⇒ 正常渲染永不触发）
FRAME_SECONDS = 0.08                 # 每帧 80 ms（codec 帧率；实测 total_s ≡ 0.080×帧数）


def stable_seed(text: str) -> int:
    """按文本派生稳定种子（sha256，不用内置 hash——后者受 PYTHONHASHSEED 影响，跨进程不一致）。

    依据（research-nex r1/r4 [7][8][10][84]）：sample_mode='fixed' 实为图内随机采样，宿主 RNG
    跨句单调推进且从不按句重播种 ⇒ 同文本每次渲染都不同（同句跨实现 F0 极差 4.10 半音）。
    传 seed 后同文本逐位可复现（实测 3/3 哈希相同）。
    **注意**：这只买到可复现性与跨句噪声相关性，实测配对 σ_render 无改善（1.08→同级），
    不要把它当成音高稳定化修复；真正的降抖动手段是跨句前缀条件化。
    """
    import hashlib
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def resolve_platform_threads(config_value, fallback: int = 4) -> int:
    """平台隔离的 ORT intra_op 线程数解析（performance-nex pn-arm-threads-001）。

    线程最优值依赖 CPU 拓扑（Intel 均匀核 vs Apple P/E 异构核），跨平台复用
    实测结论已被证明无效，因此按 platform.machine() 选段、各平台互不覆盖：

    - config_value 为 int：所有平台统一使用（兼容旧配置；不推荐新写法）
    - config_value 为 dict：{"arm64": N, "x86_64": M, "default": K}
      按 machine() 精确选段；未知平台回退 "default" 键，再回退函数 fallback。
    """
    if isinstance(config_value, dict):
        mach = platform.machine()  # "arm64" / "x86_64"
        if mach in config_value:
            return int(config_value[mach])
        if "default" in config_value:
            return int(config_value["default"])
        return int(fallback)
    if config_value is None:
        return int(fallback)
    return int(config_value)


log = logging.getLogger("moss_engine")


def runaway_frame_cap(text: str, frames_per_char: float = RUNAWAY_FRAMES_PER_CHAR,
                      buffer_frames: int = RUNAWAY_FRAME_BUFFER,
                      max_new_frames: int = 375) -> int:
    """返回该文本的「跑飞」帧数上限：超过即判为不终止。"""
    return min(int(max_new_frames),
               int(frames_per_char * max(1, len(text or "")) + buffer_frames))


def runaway_hard_cap(text: str, cap: int | None = None,
                     multiplier: int = RUNAWAY_HARD_CAP_MULTIPLIER,
                     max_new_frames: int = 375) -> int:
    """截断上限 = 检测上限的 multiplier 倍（上限为运行时的 max_new_frames）。

    为什么用倍数而不是再拟合一条帧/字曲线：检测上限已随字数缩放，
    「4× 检测上限」对短文本收紧、对长文本放宽，且保证截断只在重试彻底失败时发生。
    """
    base = runaway_frame_cap(text) if cap is None else int(cap)
    return min(int(max_new_frames), max(20, int(multiplier) * base))


class MossEngine:
    def __init__(self, model_dir: Path | None = None,
                 prompt_audio: str = "assets/audio/zh_6.wav",
                 thread_count: int = 4,   # Intel 实测 t=4（perf-20260922，ORT 1.23.2，156/156 bit-exact parity）。
                                          # ARM 平台值请经 config.toml [engine.threads] 按平台隔离配置，
                                          # 由 resolve_platform_threads() 解析后传入；勿将 Intel 值跨平台复用。
                  do_sample: bool = False,
                  runaway_max_retries: int = RUNAWAY_MAX_RETRIES):
        sys_path = str(MOSS_DIR)
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        # hf-mirror 不支持 Xet 存储协议（CAS 401）；强制走经典 HTTP 下载通道
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        from onnx_tts_runtime import OnnxTtsRuntime
        model_dir = model_dir or str(MOSS_DIR / "models")
        self.runtime = OnnxTtsRuntime(
            model_dir=model_dir,
            thread_count=thread_count,
            do_sample=do_sample,
            sample_mode="fixed",
            execution_provider="cpu",
        )
        # perf-20260922: 参考音频 codes 记忆化 —— 画像实测每句重复编码同一 prompt 约 423ms（HS-2）。
        # 缓存键 = (voice, prompt_audio_path)；确定性编码，输出 bit-exact 已验证（parity.json 156/156）。
        self._prompt_codes_cache: dict = {}
        # 合成互斥锁：ORT/codec streaming session 非线程安全。停止播放后残留的
        # 流式 AR 线程与新请求并发调用 synthesize 会互踩 session 状态（实测合成链挂死），
        # 因此所有 runtime 访问必须串行化。
        self._synth_lock = threading.Lock()
        _orig_resolve = self.runtime.resolve_prompt_audio_codes

        def _resolve_cached(*args, **kwargs):
            key = str(args) if args else (
                kwargs.get("voice", ""), kwargs.get("prompt_audio_path", ""))
            if key not in self._prompt_codes_cache:
                self._prompt_codes_cache[key] = _orig_resolve(*args, **kwargs)
            return self._prompt_codes_cache[key]

        self.runtime.resolve_prompt_audio_codes = _resolve_cached
        self.prompt_audio = prompt_audio
        self.out = "/tmp/moss_engine_out.wav"
        # 跑飞守卫的重试预算：0 = 只检测并记账，不重试（回滚到旧行为的最小开关）
        self.runaway_max_retries = max(0, int(runaway_max_retries))

    def synth(self, text: str) -> tuple[np.ndarray, int]:
        prompt = self.prompt_audio
        if not os.path.isabs(prompt):   # 相对路径锚定到 MOSS-TTS-Nano 目录
            prompt = str(MOSS_DIR / prompt)
        cap = runaway_frame_cap(text)
        hard_cap = runaway_hard_cap(text, cap)
        base_seed = stable_seed(text)
        frames = 0
        with self._synth_lock:
            for attempt in range(self.runaway_max_retries + 1):
                # 重试只换 seed、不改文本：同 (text, seed) 逐位可复现，故重试路径完全可回放
                seed = base_seed if attempt == 0 else stable_seed(f"{text}#retry{attempt}")
                result = self.runtime.synthesize(
                    text=text,
                    voice="",
                    prompt_audio_path=prompt,
                    output_audio_path=self.out,
                    sample_mode="fixed",    # P0-1 已回滚：greedy 在 macOS x86_64 ORT 走慢速内核（50.4s vs 2.8s，18x）
                    streaming=False,
                    max_new_frames=375,
                    enable_wetext=False,               # TN 需 pynini/WeTextProcessing，已验证关闭不影响音质
                    enable_normalize_tts_text=False,
                    seed=seed,                         # 同文本逐位可复现（见 stable_seed 注释）
                )
                frames = int(np.asarray(result["audio_token_ids"]).shape[0])
                if frames <= cap:
                    break
                last = attempt >= self.runaway_max_retries
                log.warning(
                    "跑飞守卫：文本 %r（%d 字）生成 %d 帧 > 上限 %d（第 %d/%d 次）%s",
                    text[:20], len(text), frames, cap, attempt + 1,
                    self.runaway_max_retries + 1,
                    "重试已用尽：将按硬上限截断交付（该单元不再参与一致性评测）" if last
                    else "换 seed 重试",
                )
            with wave.open(self.out, "rb") as w:
                sr = w.getframerate()
                pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2)
            if frames > hard_cap:
                # 兜底（研究 [151] 的实测退化形态）：重试仍不终止 ⇒ 按硬上限截断 + 淡出，
                # 不把 40 s 级别的「有声非语音」交给播放链。硬上限 = 4× 检测上限，
                # 而生产最大帧/字比 4.62 远低于检测比 5.0，故正常渲染永不进入此分支。
                keep = max(1, int(hard_cap * FRAME_SECONDS * sr))
                if len(pcm) > keep:
                    f_tail = pcm[:keep].astype(np.float32)
                    fade_len = min(max(1, int(sr * 0.008)), len(f_tail))
                    f_tail[-fade_len:, :] *= np.linspace(1.0, 0.0, fade_len)[:, None]
                    pcm = np.clip(f_tail, -32768, 32767).astype(np.int16)
                    log.warning("跑飞守卫：%d 帧 > 硬上限 %d，输出已截断为 %.2f s",
                                frames, hard_cap, len(pcm) / sr)
        # 爆破音修复：MOSS 句首从波形中段硬切入（实测首样本达 17-36% 满幅），
        # 句间拼接必产生咔哒声。处理：DC 去除 + 首 8ms 淡入 / 末 8ms 淡出。
        f = pcm.astype(np.float32)
        f -= f.mean()
        fade = max(1, int(sr * 0.008))
        f[:fade, :] *= np.linspace(0.0, 1.0, fade)[:, None]
        f[-fade:, :] *= np.linspace(1.0, 0.0, fade)[:, None]
        pcm = np.clip(f, -32768, 32767).astype(np.int16)
        return pcm, sr

    # ---- 流式合成（首帧优化，pn-arm-firstframe-001）----
    # CER 闭环裁决（n=3/模式/句）：与整段模式中位 CER 逐句相同或更好，无系统劣化。
    # 首块出声 ~114ms 且与句长无关（整段模式 371-1860ms）。

    @staticmethod
    def _chunk_to_int16_stereo(a: np.ndarray) -> np.ndarray:
        """(n, ch) float32 [-1,1] @48k → (n, ch) int16 C-contiguous。

        codec 原生输出即 48k（codec_meta codec_config.sample_rate=48000），
        无需重采样——曾误加 2x 上采样导致半速音频/CER 全崩（pn-arm-firstframe-001 教训）。
        入参可能是转置视图（非连续），PortAudio write 要求 C-contiguous，必须显式拷贝。
        """
        return np.ascontiguousarray(np.clip(a * 32767.0, -32768, 32767)).astype(np.int16)

    def synth_streaming(self, text: str):
        """流式合成 generator：yield (pcm (n,2) int16 @48k, sr=48000)。

        AR 每出一帧即经流式 codec 增量解码；通过包装 codec.run_frames 把
        每个解码块推入队列，首块即"AR 首帧生成 + 一次解码"≈110ms。
        音频内容与整段模式为同模型采样变体（非 bit-exact，CER 等价已验证）。
        """
        import queue
        import threading
        prompt = self.prompt_audio
        if not os.path.isabs(prompt):
            prompt = str(MOSS_DIR / prompt)
        q: queue.Queue = queue.Queue()
        codec = self.runtime.codec_streaming_session
        orig_run = codec.run_frames

        def timed_run(frames):
            out = orig_run(frames)
            try:
                if out is not None:
                    audio, alen = out
                    if alen and alen > 0:
                        q.put(audio[0, :, :alen].T.astype(np.float32))  # (alen, ch)
            except Exception as e:
                q.put(e)
            return out

        def worker():
            codec.run_frames = timed_run
            try:
                # 持合成锁：与整段 synth / 其他流式请求串行（session 非线程安全）。
                # 停止场景下若残留 AR 线程在跑，新请求在此排队至多一句时长。
                with self._synth_lock:
                    self.runtime.synthesize(
                        text=text, voice="", prompt_audio_path=prompt,
                        output_audio_path=self.out,
                        sample_mode="fixed", streaming=True,
                        max_new_frames=375, enable_wetext=False,
                        enable_normalize_tts_text=False, seed=stable_seed(text))
            except Exception as e:
                q.put(e)
            finally:
                codec.run_frames = orig_run
                q.put(None)

        threading.Thread(target=worker, daemon=True).start()

        first = True
        while True:
            item = q.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            pcm48 = self._chunk_to_int16_stereo(item)
            if len(pcm48) == 0:
                continue
            if first:   # 爆破音修复（流式版）：仅首块淡入；块间波形天然连续
                fade = min(len(pcm48), max(1, int(48000 * 0.008)))
                f = pcm48.astype(np.float32)
                f[:fade, :] *= np.linspace(0.0, 1.0, fade)[:, None]
                pcm48 = np.clip(f, -32768, 32767).astype(np.int16)
                first = False
            yield pcm48, 48000
