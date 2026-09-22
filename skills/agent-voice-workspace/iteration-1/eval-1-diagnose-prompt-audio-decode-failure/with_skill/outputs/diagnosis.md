# 诊断报告：TTS 守护进程启动崩溃 — torchaudio/torchcodec 解码参考音频失败

> 诊断演练（只读）：本文档仅基于 `skills/agent-voice/SKILL.md`（「已知问题与修复」一节）与
> `scripts/MOSS-TTS-Nano/onnx_tts_runtime.py` / `scripts/onnx_tts_runtime.py` 的静态阅读得出，
> 未对系统做任何修改、未重装依赖、未重启服务。

## 一、现象

- ttsd 守护进程一启动即崩（KeepAlive 循环重启），报错：

  ```
  RuntimeError: Failed to decode audio samples: decode_av_frame,
  .../torchcodec/src/torchcodec/_core/SingleStreamDecoder.cpp:1655,
  Could not receive frame from decoder: Invalid data found when processing input
  ```

- 调用链：`_load_reference_audio → torchaudio.load → load_with_torchcodec`。
- 出错位置：加载声音克隆参考音频 `assets/audio/zh_6.wav`。
- 已排除项：sox 能正常读该 wav（文件本身完好）；ffmpeg 为 brew 最新 9.x；TTS 模型已下载齐全（排除「hf-mirror Xet 静默下载失败」问题）。

## 二、根因

**torchaudio 2.9+ 移除了 soundfile 解码后端并强制走 torchcodec，而 torchcodec 预编译 wheel 与系统 FFmpeg 8/9 不兼容。**

SKILL.md「已知问题与修复」原文（torchaudio 2.9+ 解码参考音频失败 一节）：

> torchaudio 2.9 起移除 soundfile 后端并强制 torchcodec，而 torchcodec 预编译 wheel 与系统 FFmpeg 8/9 不兼容。

崩溃路径逐层对应：

1. torchaudio ≥2.9 调用 `load()` 时不再使用 libsndfile/soundfile，而是路由到 torchcodec 的 C++ 解码器（`SingleStreamDecoder.cpp`）。
2. torchcodec wheel 内的解码代码通过 FFmpeg 动态库（avcodec/avformat）工作，其预编译版本针对旧版 FFmpeg ABI；本机 brew 装的 FFmpeg 9.x 与之不兼容。
3. 于是 FFmpeg 解码器返回 `AVERROR_INVALIDDATA`，被 torchcodec 包装成 `Could not receive frame from decoder: Invalid data found when processing input`，再被 torchaudio 包装为 `Failed to decode audio samples`。守护进程在引擎初始化阶段加载 prompt 音频时抛出该异常 → 启动即崩。

**为什么「修复已内置」却仍然崩——仓库证据**：skill 声称修复已内置在 `_load_reference_audio`，但代码库里存在**两份**该文件：

| 文件 | `_load_reference_audio` 实现 | 状态 |
|---|---|---|
| `scripts/MOSS-TTS-Nano/onnx_tts_runtime.py`（L445–455） | 先 `soundfile.read(dtype="float32", always_2d=True)` 读，失败才回落 `torchaudio.load`；带注释说明 torchcodec × FFmpeg 8/9 问题 | ✅ 已修复版 |
| `scripts/onnx_tts_runtime.py`（L446） | 直接 `torchaudio.load(...)`，无 soundfile 分支 | ❌ 陈旧副本 |

崩溃日志调用链是 `torchaudio.load → load_with_torchcodec`，说明**实际被 ttsd 加载执行的是陈旧副本**（`scripts/onnx_tts_runtime.py` 或目标机上未同步的旧版），而非 MOSS-TTS-Nano 下已修复的那份。这是本次崩溃的直接触发条件。

## 三、为什么 sox 能读、torchaudio 却失败

这不是音频文件损坏，而是**解码后端不匹配**：

- **sox** 走自己链接的 libsndfile 解码路径，与 FFmpeg 无关，自然能读；只能证明「文件数据完好」，不能证明「所有解码器都能读」。
- **torchaudio ≥2.9** 已不走 libsndfile：所有解码统一经 torchcodec → 系统 FFmpeg 动态库。FFmpeg 9 的 ABI/API 与 torchcodec 预编译 wheel 不兼容，导致对一个完全合法的 WAV 解码失败。
- 换句话说，「文件没问题 + ffmpeg 是最新版」恰恰与故障自洽：ffmpeg 越新，与 torchcodec 旧 wheel 的 ABI 差距越大。`Invalid data found when processing input` 是 FFmpeg `AVERROR_INVALIDDATA` 的通用文案，容易误导成「文件坏了」，实际是解码器/库版本错配。

## 四、具体修复步骤（本次演练不执行）

原则：**走 skill 内置的代码级修复，不动系统依赖**。SKILL.md 明确警告「不要升级到不兼容组合后只改 torchaudio 版本」。

1. **确认实际加载的模块**（只读排查）：查看崩溃 traceback 中的文件路径，或
   ```bash
   ps aux | grep ttsd
   .venv-moss/bin/python -c "import torchaudio, torchcodec; print(torchaudio.__version__)"
   ```
   若 traceback 指向 `scripts/onnx_tts_runtime.py`（不在 MOSS-TTS-Nano 目录下），即坐实陈旧副本。
2. **同步修复**：用 `scripts/MOSS-TTS-Nano/onnx_tts_runtime.py` 中已修复的 `_load_reference_audio`（soundfile 优先 + torchcodec 兜底）覆盖/替换陈旧副本的对应实现；或让 ttsd 的导入路径指向 MOSS-TTS-Nano 下的修复版模块。
3. **不要**采用降级 torchaudio / 升降 ffmpeg 这类系统级改法作为主修复；它们改动面大且 skill 已判为错误方向。
4. 修复落盘后重启守护进程生效：`launchctl kickstart -k gui/$(id -u)/com.moss.ttsd`（由用户/运维执行，本演练不执行）。

## 五、如何验证修复

按代价从小到大：

1. **单点复现对照（只读、不碰服务）**：
   ```bash
   cd scripts
   # 应成功打印 (channels, samples)，证明文件与 soundfile 路径都正常：
   .venv-moss/bin/python -c "import soundfile as sf; d,sr=sf.read('../assets/audio/zh_6.wav',dtype='float32',always_2d=True); print(d.shape,sr)"
   # 修复前应复现崩溃同款 RuntimeError，坐实根因；修复后经 soundfile 分支不再走到这里
   .venv-moss/bin/python -c "import torchaudio; print(torchaudio.load('../assets/audio/zh_6.wav'))"
   ```
2. **端到端朗读**：`./scripts/run.sh "你好，世界"` → 守护进程完成引擎初始化、无 `Failed to decode audio samples`，BlackHole 有输出。
3. **守护进程稳定性**：`launchctl print gui/$(id -u)/com.moss.ttsd` 观察 PID 稳定不再被 KeepAlive 循环重启；日志无解码报错。
4. **回归自测**：`cd scripts && .venv-moss/bin/python selftest.py`，`selftest_report.json` 中 T1–T5 通过、overall=pass。
5. **收音确认**（可选）：sox 从 "BlackHole 2ch" 录 9s 后 `sox /tmp/bh.wav -n stat | grep RMS`，RMS≈0.06–0.14 即声音通路正常。

## 六、结论一句话

wav 文件与模型都没问题；根因是 torchaudio 2.9+ 强制 torchcodec 解码、torchcodec wheel 与系统 FFmpeg 9 ABI 不兼容，而守护进程实际运行的是 `scripts/onnx_tts_runtime.py` 这份**未含 soundfile 兜底修复的陈旧副本**——用 MOSS-TTS-Nano 目录下已修复的 `_load_reference_audio` 同步过去即可，无需动 ffmpeg/torchaudio。
