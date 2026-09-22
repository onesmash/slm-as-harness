#!/usr/bin/env python3
"""moss_engine.py — MOSS-TTS-Nano ONNX 引擎适配器（质量档，单声音原生中英混读）。

依赖：.venv-moss（py3.12 + onnxruntime + torch2.2.2 + transformers）+ MOSS-TTS-Nano 仓库文件
许可：Apache-2.0
注意：MOSS 为自回归模型，本机（Intel CPU）RTF≈0.6-1.3；threads=4 实测最优（perf-20260922，ORT 1.23.2）。
接口与其他引擎一致：synth(text) -> (48k 立体声 int16, sr)
"""
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


class MossEngine:
    PREFIX_WINDOW = 2          # 前缀窗：最近 ≤2 句（实测优于无限累积，成本仅其 57%）
    PREFIX_MIN_FRAMES = 4      # 退化前缀门控：<4 帧的上一句不入窗
    PREFIX_RESET_TIMEOUT_S = 20.0   # 静默超过此时长视为新会话

    def __init__(self, model_dir: Path | None = None,
                 prompt_audio: str = "assets/audio/zh_6.wav",
                 thread_count: int = 4,   # Intel 实测 t=4（perf-20260922，ORT 1.23.2，156/156 bit-exact parity）。
                                          # ARM 平台值请经 config.toml [engine.threads] 按平台隔离配置，
                                          # 由 resolve_platform_threads() 解析后传入；勿将 Intel 值跨平台复用。
                  do_sample: bool = False):
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
        # ── 跨句前缀条件化（research-nex r4，实测句间 F0 极差 −49.3% / SD −45.3%，成本 +81.9 ms/句）──
        # 注入点是 resolve_prompt_audio_codes：返回「参考 codes + 最近 ≤2 句 codes」。
        # 会话状态必须被清空，否则跨请求继承上段韵律（一次错前缀即 +4.55 半音）；
        # 清空时机 = 新文本 / 换语音 / 换 prompt / 超时 / 停止 五类事件。
        self._prefix_frames: list = []          # 最近 ≤PREFIX_WINDOW 句的帧列表
        self._prefix_prompt_key = None          # 换 prompt ⇒ 清空
        self._prefix_last_t = 0.0               # 静默超时 ⇒ 清空
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
            ref = self._prompt_codes_cache[key]
            if not self._prefix_frames:
                return ref
            # 参考 codes + 最近 ≤2 句 codes。上游 build_audio_prefix_rows 只遍历「帧行」，
            # 故返回帧列表拼接即可，无需改上游代码（零改动注入点）。
            # 注意展平：_prefix_frames 是「每句一个帧列表」的两层结构，而上游要的是
            # 扁平帧序列（build_audio_prefix_rows 逐帧取 code_row[index]）。曾按两层拼接
            # 导致 int(list) 报错——此处显式展平。
            return list(ref) + [_frame for _sent in self._prefix_frames for _frame in _sent]

        self.runtime.resolve_prompt_audio_codes = _resolve_cached
        self.prompt_audio = prompt_audio
        self.out = "/tmp/moss_engine_out.wav"

    def reset_prefix_state(self, reason: str = "") -> None:
        """清空跨句前缀窗。调用时机（五类事件）：新文本 / 换语音 / 换 prompt / 超时 / 停止。

        由守护进程在每次请求开始时调用（见 ttsd.py 的 serve()），超时与换 prompt 另在
        _prefix_guard() 内兜底。不清空的后果是把上一段文本的韵律带进新请求。
        """
        self._prefix_frames = []
        self._prefix_last_t = time.time()

    def _prefix_guard(self, prompt: str) -> None:
        """会话边界守卫：换 prompt 或静默超时即清空（新文本/换语音/停止由调用方显式重置）。"""
        if prompt != self._prefix_prompt_key:
            self._prefix_prompt_key = prompt
            self._prefix_frames = []
        elif self._prefix_frames and (time.time() - self._prefix_last_t) > self.PREFIX_RESET_TIMEOUT_S:
            self._prefix_frames = []

    def _record_sentence_codes(self, result) -> None:
        """把本句生成的 audio codes 记入前缀窗（≤2 句；<4 帧的退化句不入窗）。"""
        ids = result.get("audio_token_ids") if isinstance(result, dict) else None
        if ids is None:
            return
        rows = ids.tolist() if hasattr(ids, "tolist") else [list(r) for r in ids]
        if len(rows) < self.PREFIX_MIN_FRAMES:      # 门控：过短前缀无信息且易放大噪声
            return
        self._prefix_frames.append(rows)
        while len(self._prefix_frames) > self.PREFIX_WINDOW:
            self._prefix_frames.pop(0)
        self._prefix_last_t = time.time()

    def synth(self, text: str) -> tuple[np.ndarray, int]:
        prompt = self.prompt_audio
        if not os.path.isabs(prompt):   # 相对路径锚定到 MOSS-TTS-Nano 目录
            prompt = str(MOSS_DIR / prompt)
        self._prefix_guard(prompt)
        with self._synth_lock:
            _result = self.runtime.synthesize(
                text=text,
                voice="",
                prompt_audio_path=prompt,
                output_audio_path=self.out,
                sample_mode="fixed",    # P0-1 已回滚：greedy 在 macOS x86_64 ORT 走慢速内核（50.4s vs 2.8s，18x）
                streaming=False,
                max_new_frames=375,
                enable_wetext=False,               # TN 需 pynini/WeTextProcessing，已验证关闭不影响音质
                enable_normalize_tts_text=False,
                seed=stable_seed(text),            # 同文本逐位可复现（见 stable_seed 注释）
            )
            self._record_sentence_codes(_result)   # 记入跨句前缀窗（锁内，避免与流式请求交叉）
            with wave.open(self.out, "rb") as w:
                sr = w.getframerate()
                pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2)
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
                    _result = self.runtime.synthesize(
                        text=text, voice="", prompt_audio_path=prompt,
                        output_audio_path=self.out,
                        sample_mode="fixed", streaming=True,
                        max_new_frames=375, enable_wetext=False,
                        enable_normalize_tts_text=False, seed=stable_seed(text))
                    self._record_sentence_codes(_result)
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
