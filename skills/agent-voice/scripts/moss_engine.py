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
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent          # scripts/
BASE = ROOT.parent                               # tts-mic-loopback/
MOSS_DIR = ROOT / "MOSS-TTS-Nano"


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

    def synth(self, text: str) -> tuple[np.ndarray, int]:
        prompt = self.prompt_audio
        if not os.path.isabs(prompt):   # 相对路径锚定到 MOSS-TTS-Nano 目录
            prompt = str(MOSS_DIR / prompt)
        self.runtime.synthesize(
            text=text,
            voice="",
            prompt_audio_path=prompt,
            output_audio_path=self.out,
            sample_mode="fixed",    # P0-1 已回滚：greedy 在 macOS x86_64 ORT 走慢速内核（50.4s vs 2.8s，18x）
            streaming=False,
            max_new_frames=375,
            enable_wetext=False,               # TN 需 pynini/WeTextProcessing，已验证关闭不影响音质
            enable_normalize_tts_text=False,
        )
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
