#!/Users/xuhui/Code/research/research-output/tts-mic-loopback/.venv-moss/bin/python
"""moss_engine.py — MOSS-TTS-Nano ONNX 引擎适配器（质量档，单声音原生中英混读）。

依赖：.venv-moss（py3.12 + onnxruntime + torch2.2.2 + transformers）+ MOSS-TTS-Nano 仓库文件
许可：Apache-2.0
注意：MOSS 为自回归模型，本机（Intel CPU）RTF≈1-2；threads=2 最优（1 慢 20%，4 慢 25%）。
接口与其他引擎一致：synth(text) -> (48k 立体声 int16, sr)
"""
import os
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent          # scripts/
BASE = ROOT.parent                               # tts-mic-loopback/
MOSS_DIR = ROOT / "MOSS-TTS-Nano"


class MossEngine:
    def __init__(self, model_dir: Path | None = None,
                 prompt_audio: str = "assets/audio/zh_6.wav",
                 thread_count: int = 2,   # P0 修复：留核给 USB 音频通路防欠载爆破音（实测 RTF 无损失 0.85 vs 0.86）
                 do_sample: bool = False):
        sys_path = str(MOSS_DIR)
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        from onnx_tts_runtime import OnnxTtsRuntime
        model_dir = model_dir or str(MOSS_DIR / "models")
        self.runtime = OnnxTtsRuntime(
            model_dir=model_dir,
            thread_count=thread_count,
            do_sample=do_sample,
            sample_mode="fixed",
            execution_provider="cpu",
        )
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
