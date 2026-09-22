# 诊断报告：TTS 守护进程启动崩溃（torchaudio/torchcodec 解码 WAV 失败）

- **现象**：agent-voice 的 TTS 守护进程一启动就崩，加载声音克隆参考音频 `assets/audio/zh_6.wav` 时抛：
  `RuntimeError: Failed to decode audio samples: decode_av_frame, .../torchcodec/src/torchcodec/_core/SingleStreamDecoder.cpp:1655, Could not receive frame from decoder: Invalid data found when processing input`
  （调用链 `torchaudio.load → load_with_torchcodec`）
- **已排除项**：sox 能正常读该 wav；brew 的 ffmpeg 为最新 9.x；TTS 模型已下载齐全。
- **依据材料**：`skill-snapshot/SKILL.md`、`skill-snapshot/references/DEPLOYMENT.md`（§6.11）、`skill-snapshot/scripts/onnx_tts_runtime.py` 与 `skill-snapshot/scripts/MOSS-TTS-Nano/onnx_tts_runtime.py` 的 `_load_reference_audio`。

## 一、根因

**这不是音频文件损坏，而是音频解码后端不兼容：部署机器在运行旧版 runtime（直接调 `torchaudio.load`），而 torchaudio 2.9+ 已移除 soundfile/sox 后端、强制走 torchcodec；torchcodec 依赖系统 FFmpeg 动态库，与 brew 安装的 FFmpeg 9.x 组合时对部分 WAV 解码直接报 `Invalid data`。**

证据链：

1. 崩溃调用链出现 `load_with_torchcodec` —— 说明解码走的是 torchcodec/FFmpeg 通道，而不是任何 sox/libsndfile 通道。
2. 快照里存在两份 `_load_reference_audio`：
   - 旧版 `scripts/onnx_tts_runtime.py:446`：无条件 `torchaudio.load(...)`；
   - 修复版 `scripts/MOSS-TTS-Nano/onnx_tts_runtime.py:445-455`：注释明确写着"torchaudio 2.9+ 移除 soundfile 后端并强制走 torchcodec；torchcodec 依赖系统 FFmpeg 动态库，**FFmpeg 8/9 下对部分 WAV 解码失败（Invalid data）**"，并改为优先用 soundfile 读 WAV/FLAC、其余格式才回落 torchcodec。
   现场报错走的正是旧代码路径，说明部署未切到修复版。
3. torchcodec 官方支持的 FFmpeg 主版本矩阵为 4–7（多数已发布版本不含 8/9）。brew 最新版 ffmpeg=9.x，`decode_av_frame` 在 avcodec send/receive 循环里返回 `AVERROR_INVALIDDATA`，torchcodec 将其包装成上述 RuntimeError。
4. 守护进程在引擎初始化阶段就执行 `encode_reference_audio → _load_reference_audio`（参考音频要在启动时编码成 prompt codes），因此解码一失败进程立即退出；launchd KeepAlive（DEPLOYMENT §6.12）会不断重拉，表现为"一启动就崩"的循环。

## 二、为什么 sox 能读、torchaudio 却失败

两者用的是**完全独立的两套解码栈**，文件本身没问题：

| 工具 | 解码栈 | 是否依赖系统 FFmpeg |
|---|---|---|
| sox | 自带 RIFF/WAV 解析器 + PCM 解码器（brew sox 不链 ffmpeg） | 否 |
| torchaudio < 2.9（旧"sox 后端"） | 通过 sox 读取 | 否（此通道在 2.9+ 已删除） |
| torchaudio ≥ 2.9 | torchcodec → libavformat/libavcodec = brew FFmpeg 9.x | **是** |

所以 sox 读得动只证明 RIFF 容器和 PCM 样本完好；torchaudio 失败发生在 FFmpeg 9 + torchcodec 这条新链路上，属于版本组合缺陷。另注意 DEPLOYMENT §6.11 的历史坑：该仓库 prompt 音频曾出现"假 wav"（zh_1 实为 FLAC、zh_10/zh_11 实为 MP3 仅扩展名 .wav），所以不能仅凭扩展名判断格式——但本次即使文件是标准 RIFF/pcm_s16le，FFmpeg 9 下同样会触发该已知失败，解码链路仍是主因。

## 三、具体修复步骤（按 skill 内已验证方案，优先级从高到低）

1. **换用修复版 `_load_reference_audio`（推荐，skill 已实测）**
   让部署引用 `scripts/MOSS-TTS-Nano/onnx_tts_runtime.py` 的实现：优先 soundfile 读取（libsndfile 原生解 WAV，不经 FFmpeg），失败才回落 torchaudio/torchcodec：

   ```python
   def _load_reference_audio(self, reference_audio_path: str | Path) -> np.ndarray:
       path = str(Path(reference_audio_path).expanduser().resolve())
       try:
           import soundfile as _sf
           data, sample_rate = _sf.read(path, dtype="float32", always_2d=True)
           waveform = torch.from_numpy(data.T)   # (channels, time)，与 torchaudio.load 语义一致
       except Exception:
           waveform, sample_rate = torchaudio.load(path)
       ...
   ```

   ⚠️ 检查 `ttsd.py`/`moss_engine.py` 实际 import 的是哪份模块：快照里新旧两份并存，必须确保守护进程加载的是打过补丁的那份（可用 `python -c "import onnx_tts_runtime, inspect; print(inspect.getsourcefile(onnx_tts_runtime))"` 确认）。
2. **校验参考音频为"真 WAV"**（按 DEPLOYMENT §6.11 标准）：`file assets/audio/zh_6.wav` 应显示 `RIFF (little-endian) data, WAVE audio, Microsoft PCM, ...`；若不是，用 ffmpeg 重编码：
   `ffmpeg -i assets/audio/zh_6.wav -c:a pcm_s16le assets/audio/zh_6_fixed.wav`（先备份原文件，改完同步 `config.toml [engine] prompt_audio`）。
3. **（可选的环境级兜底，本次练习不执行）**：把 torchaudio 钉在 < 2.9 保留 soundfile 后端；或安装与 FFmpeg 9 匹配的 torchcodec 版本 / 将 brew ffmpeg 回退到 7.x。改动更大且 skill 未验证，仅在方案 1 不可用时考虑。

## 四、如何验证修复

1. **最小复现对照**（不起守护进程）：
   ```bash
   .venv-moss/bin/python - <<'PY'
   import torchaudio, soundfile as sf
   p = "assets/audio/zh_6.wav"
   print(sf.info(p))                       # 确认真 WAV、采样率/声道/时长
   data, sr = sf.read(p, dtype="float32", always_2d=True)
   print("soundfile OK:", data.shape, sr)  # 修复路径应成功
   try:
       torchaudio.load(p)                  # 旧路径预期仍抛 torchcodec RuntimeError（阴性对照）
   except RuntimeError as e:
       print("torchcodec path still fails (expected):", e)
   PY
   ```
   soundfile 成功 + torchaudio 失败，即坐实"解码后端问题而非文件损坏"。
2. **重启守护进程验证**：必须 `launchctl unload` 后再 `load`（直接 pkill 会被 KeepAlive 拉起）；观察 `ttsd_launchd.log`：
   - 修复前：日志里反复出现"加载引擎"+ torchcodec RuntimeError（崩溃循环）；
   - 修复后：只有一次"加载引擎"，无 RuntimeError，进程稳定存活。
3. **端到端验证**：`./scripts/ttsay.py "测试朗读"` 正常出声；BlackHole 输入端 RMS 落在文档区间（zh_6 女声本身轻柔，≈0.03–0.08 为正常，§6.11/§6.13）；`./scripts/selftest.py` T1–T5 全过（尤其 T1 合成出非静音 WAV）。

## 五、结论一句话

`zh_6.wav` 文件没坏——坏的是解码链：旧版 runtime 的 `torchaudio.load` 在 torchaudio 2.9+ 下被强制路由到 torchcodec，而 torchcodec 与 brew FFmpeg 9.x 不兼容；按 skill 已验证方案把 `_load_reference_audio` 换成 soundfile 优先的实现并重启守护进程即可修复，无需动音频文件之外重装任何依赖。
