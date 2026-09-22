---
name: agent-voice
description: "在 macOS 上从零搭建'文本→本地 TTS→虚拟麦克风'系统并正确运行。当用户想要把文字转成语音并通过虚拟麦克风输出给其他应用（Zoom/微信/录音软件等）时使用此 skill。覆盖：MOSS-TTS-Nano ONNX 引擎部署、BlackHole 虚拟声卡安装与配置、launchd 常驻服务、品牌词发音映射、爆破音修复、闭环 CER 评分。即使用户只说'读一下这段文字'或'帮我搭个 TTS'，只要涉及本地语音合成输出到虚拟麦克风，就应使用此 skill。也适用于系统已装好但朗读失败、守护进程崩溃重启、BlackHole 静默等故障排查场景。"
---

# TTS 虚拟麦克风系统 — Agent 操作指南

## 系统做什么

```
用户文本 → MOSS 本地合成 → BlackHole 2ch（虚拟麦克风）→ 其他 App 收音
                                                    └→ monitor 同播（本地可听）
```

把文字转成语音，通过 BlackHole 虚拟声卡"假装"成麦克风输入。任何 App（Zoom、微信、QuickTime…）把麦克风切到 **BlackHole 2ch** 就能收到合成语音。

**播放入口只有一个：`./scripts/run.sh`**（朗读、停止都走它）。不要绕过它去直接执行 `scripts/` 里的 python 脚本——原因见[朗读文本](#朗读文本)。

## 快速部署（推荐）

```bash
./scripts/setup.sh
```

一键完成：前置检查 → venv → Python 依赖 → launchd 服务 → 等待守护进程就绪 → selftest。

两个环节会退出并要求**用户在终端人工执行**（脚本无法代输密码），按提示操作后重跑即可：
- **BlackHole 安装**：`brew install --cask blackhole-2ch` 的 pkg 安装器需要 sudo 密码，agent 直接跑必失败——不要尝试绕过，直接交给用户。
- 完成后 `sudo killall coreaudiod` 加载设备（macOS 15+ 上 `launchctl kickstart` 系统服务会被 SIP 拦截，用 `killall` 替代）。

**首次启动会自动下载 MOSS 模型 ~730MB**（走 hf-mirror 镜像，落盘到 `scripts/MOSS-TTS-Nano/models/`），属于正常流程，不要在下载中途判定为卡死。

## 前置条件（setup.sh 会逐项检查）

| 项 | 要求 | 检查命令 |
|---|---|---|
| macOS | 12+ | `sw_vers` |
| BlackHole 2ch | 已安装 | `system_profiler SPAudioDataType \| grep BlackHole` |
| Python 3.12 | venv 用 | `python3.12 --version`（缺则 `brew install python@3.12`） |
| sox + ffmpeg | 音频处理/CER 评分 | `which sox ffmpeg`（缺则 `brew install sox ffmpeg`） |

手动部署（备查，等价于 setup.sh 各步骤）：

```bash
cd scripts/
python3.12 -m venv .venv-moss
# 版本 pin 按平台隔离（同 setup.sh，勿跨平台复用）：x86_64 必须锁——Intel macOS 上 torch 止步
# 2.2.2，numpy 2.x 会让 torch .numpy() 报 "Numpy is not available"；transformers 5.x 还要求
# torch>=2.5 会静默禁用 torch 后端。arm64 有持续更新的轮子，按原样不锁。
.venv-moss/bin/pip install "numpy<2" "onnxruntime==1.23.2" sentencepiece sounddevice soundfile \
  "transformers==4.57.1" "piper-tts==1.8.0" cn2an pypinyin pypinyin-dict jieba ordered-set \
  "torch==2.2.2" "torchaudio==2.2.2" torchcodec huggingface_hub   # 后五个是 MOSS 引擎运行必需，不可省
# launchd：plist 由 com.moss.ttsd.plist.tmpl 模板按本机路径实例化（见 setup.sh 第 4 步）
# 守护进程只由 launchd 管理：不要手动再起一个实例（历史上会造成实例风暴）
```

## 朗读文本

```bash
./scripts/run.sh "要朗读的文本"   # 朗读：阻塞至播放完成；文本可含换行，整段作为单个参数传入
./scripts/run.sh "$(cat 稿子.txt)"  # 长文本/多行：用命令替换整段传入，仍是同一个入口（不要用管道）
./scripts/run.sh --stop          # 停止当前播放（可从另一个终端/连接发起）
```

`run.sh` 自己不含合成逻辑，只做两件事：定位 `.venv-moss` 的 python、把参数原样转给它背后的常驻
服务客户端；客户端把文本交给 ttsd 守护进程，阻塞到播放结束，并打印首音延迟/音频时长/句数。

**为什么只留这一个入口**：脚本 shebang 是 `#!/usr/bin/env python3`，而依赖只装在 `.venv-moss` 里，
绕过 `run.sh` 直接执行脚本会因系统 python 缺依赖报 ImportError；更关键的是，"直连合成"或"手动起
服务"这类旁路都会绕开常驻服务——首音更慢、播放状态无人管理，历史上还出现过多个管理器抢 socket/
音频流的实例风暴。排障时也从 `run.sh` 出发，不要临时改走别的入口。

**守护进程不在时的预期行为**：`run.sh` 不自己拉起守护进程，只等 launchd（KeepAlive）拉起，最多等
60s；冷启动首个请求要加载+预热引擎（Apple Silicon ~5s，Intel 15–71s），期间没有输出属正常现象，
不要判定为卡死，也不要手动再起一个实例。

**停止语义**：`--stop` 置会话停止信号，两路输出（monitor 扬声器 + BlackHole 虚拟麦）在当前
0.2s 子块播完后丢弃剩余块（≤0.2s 内静音）；被停止的会话回 `done(stopped=true)`，守护进程状态
干净、后续请求正常。monitor 为会话级常驻流 + 独立线程块级写（**不是** afplay 子进程——afplay
每块启停的间隙曾是"播放开头卡顿"的根因）；实现全程不 abort/close 音频流（CoreAudio 状态破坏
与同设备重开挂起均已实测）。

## 配置（config.toml）

```toml
[engine]
name = "moss"           # moss（质量档）| say（零安装兜底）
prompt_audio = "assets/audio/zh_6.wav"  # 声音克隆参考音频（换声音=换这个文件）
number_normalize = true  # 数字→中文读法（12306→一万二千三百零六）
hf_endpoint = "https://hf-mirror.com"   # 模型下载镜像

[device]
name = "BlackHole 2ch"
blocksize = 256         # 实测最优（RTF 无损失）
latency = "low"         # 必须显式 low；默认提示为 high

[monitor]
enabled = true           # 本地同播（扬声器/耳机同步可听）
```

**用户覆盖**：`~/.config/agent-voice/config.toml` 存在时，ttsd.py 以内置 `scripts/config.toml` 为基底**逐键合并**（用户优先；dict 递归合并，标量/列表整体替换），用户配置只需写要改的键。改配置后需重启守护进程生效（`launchctl kickstart -k gui/$(id -u)/com.moss.ttsd`）。

## 架构

```
文本 → cn2an 数字归一化 → 品牌词映射 → 句级切分(≤60字)
  → MOSS AR 合成（逐句流水线）→ 有界队列(4)
    → BlackHole 输出（虚拟麦克风 → 其他 App）
    → 会话级常驻输出流（monitor → 本地扬声器/耳机）
```

## 性能基线

| 指标 | Intel MBP 实测 | Apple Silicon 实测（M4 Pro，2026-09） |
|---|---|---|
| 稳态合成 RTF | 0.85–1.05（threads=2） | 0.18–0.21 |
| 首帧延迟（热态，流式） | —（未启用） | **81–170ms，与句长无关**（整段模式 428–1470ms） |
| 引擎冷启动（加载+预热） | 15–71s | ~5s（含流式 kernel + 首连接开流/校准预热） |
| BlackHole 同流全双工回环 @256/512/1024 帧（48kHz，T5） | 26.7/32.0/64.0ms（= 1280/1536/3072 采样 = 5/3/3 个 blocksize 缓冲周期） | 同左（缓冲周期计数，**与 CPU 架构无关**） |

> **口径（T5 当前实现）**：`scripts/tools/measure_first_audio.py` 用 `sd.playrec` 在**同一 PortAudio 全双工流**内播放「0.3s 前导 + 50ms 1kHz burst」，以互相关定位 burst 到达样本，取「到达样本 − 理论样本」。该值恒为 blocksize 的整数倍（5/3/3 个回调周期），由 PortAudio/CoreAudio/BlackHole 缓冲深度决定，**不随 CPU 架构变化**—— Intel 与 Apple Silicon 数值相同不是巧合；仅当 blocksize、采样率或 BlackHole/macOS 版本变化时才会变。它不是声学/硬件时延（BlackHole 自报 out+in 缓冲为 16.0/21.3/42.7ms）。
> **历史口径（2026-09-18 首装，已废弃，勿与上表并列比较）**：旧 `measure_first_audio.py`（双标记差分版，脚本已随工作区删除、不在本仓库）给出 `abs_p50 = 205.4/216.0/226.7ms`，减去 200ms 合成延迟参数得 **5.4/16.0/26.7ms**——该三值均**小于**同表 PortAudio 自报 out+in 缓冲（16.0/21.3/42.7ms），故不可能是真实回环时延，仅为锚定在自报 `Stream.latency` 上的残差。

两代硬件绝对值差异大，但**相对行为一致**（RTF 远小于 1 即健康）。判断健康看趋势，不要硬套另一台机器的数值——**回环延迟一项两代口径不同**（新口径不线性：+5.3/+32.0ms；旧口径线性：每 +256 帧 ≈ +10.7ms），不可跨机器/跨版本直接比较。

### 首帧流式合成

`config.toml [engine] streaming_first_audio`：**内置 config.toml 出厂为 `false`（整段模式）**——它是下方「播放开头卡顿（LaunchAgent QoS）」问题最可靠的缓解，故默认不启用（实测首音 1.0–1.7s，落在整段模式 428–1470ms 区间内属预期）；键缺失时代码兜底为 `true`（`ttsd.py`）。设为 `true` 启用流式：首句 AR 逐帧解码出块，首块出声 ~85–170ms 且与句长无关；整段模式为 428–1470ms（随首块字数线性增长）。CER 闭环 n=3 无系统劣化（pn-arm-firstframe-001）；音频为采样变体（非 bit-exact，听感建议人工确认一次）。回滚：设为 `false`。排障：daemon 日志 grep「回落」可发现流式异常静默回退整段。

### 平台隔离调优（重要）

ORT 线程数等 CPU 拓扑敏感参数**按平台隔离配置、互不复用**（`config.toml [engine.threads]`）：

```toml
[engine.threads]
default = 4        # 未识别平台回退
x86_64 = 4         # Intel 实测（perf-20260922）
arm64 = 4          # M4 Pro 实测（pn-arm-threads-001）：t=1 +31.6%、t=12 +22.7%（E 核）均显著劣化
```

- 各平台实测值独立回填，**任何平台的调优结论不得直接写入另一平台段**
- 换芯片/换拓扑后只重测自己那段（harness: `agent-voice-workspace/performance-nex/bench_threads.py`）
- 解析逻辑 `moss_engine.resolve_platform_threads()` 按 `platform.machine()` 选段，未知平台走 `default`
- 用户覆盖同理：`~/.config/agent-voice/config.toml` 只写要改的平台段，其他平台不受影响

## 已知问题与修复（全部经实测验证）

> **音调/韵律稳定性**的完整诊断与修复记录（现象归属裁决、根因链、四条已实施修复的实测数字与代价、
> 五个已证伪杠杆、验收判据与局限）见 [`references/PITCH_STABILITY_REPORT.md`](references/PITCH_STABILITY_REPORT.md)。
> 要点：逐句独立随机实现 + 标点孤儿块 + 增益自噬三因叠加；验收**不要**用句间 F0 SD（合成已比自然人声更稳）。

### 模型下载静默失败：hf-mirror 不支持 Xet 协议
**症状**：守护进程反复崩溃重启（KeepAlive 循环）；日志 `RuntimeError: ... cas-server.xethub.hf.co ... 401 Unauthorized`，随后 `FileNotFoundError: codec_browser_onnx_meta.json`。models 目录只有几百 KB 的 json、没有 onnx/data。
**根因**：huggingface_hub ≥1.0 默认走 Xet 存储协议，hf-mirror 只代理经典 HTTP 通道。
**修复**：已内置——`moss_engine.py` 设置 `HF_HUB_DISABLE_XET=1`。若诊断其他环境，先查该环境变量；手动补下载：
```bash
HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
  .venv-moss/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX', local_dir='MOSS-TTS-Nano/models/MOSS-TTS-Nano-100M-ONNX')"
# codec 同理: repo_id='OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX'
```

### torchaudio 2.9+ 解码参考音频失败（torchcodec × FFmpeg 9）
**症状**：`RuntimeError: Failed to decode audio samples ... Invalid data found when processing input`，发生在加载 prompt 音频（zh_6.wav）时。
**根因**：torchaudio 2.9 起移除 soundfile 后端并强制 torchcodec，而 torchcodec 预编译 wheel 与系统 FFmpeg 8/9 不兼容。
**修复**：已内置——`onnx_tts_runtime.py` 的 `_load_reference_audio` 优先用 soundfile 读 WAV/FLAC，其余格式回落 torchcodec。不要升级到不兼容组合后只改 torchaudio 版本。

### BlackHole 回环校准误判（已修复的坑，勿回退）
**症状**：日志 `回环校准: 实测 RMS=0.0000 → 增益 ×40.0`，之后播放动态范围被压坏。
**根因**：校准音经回环需要时间；其他 App 占用 BlackHole 输入端或流启动延迟都会读到近零。**近零 ≠ 设备音量衰减**（真实衰减特征是 RMS≈0.001x）。
**修复**：已内置——RMS<0.005 视为测量失败保持增益 ×1.0，并加长校准窗口到 0.5s+0.7s。
**注意**：校准期间不要用 sox 等工具同时从 BlackHole 输入端录音，会互相干扰。

### BlackHole 音量被系统重置到近零（-40dB）
**症状**：回环录音 RMS≈0.001x（正常 0.06–0.14）。
**修复**：v2 音量策略不碰系统音量——ttsd 用"启动校准 + 数字域自动增益"补偿（用户音量不受影响）。`fix_blackhole_volume.sh` 保留为手动兜底。

### USB 声卡插拔后输出流句柄过期
**症状**：守护进程在合成（CPU 高）但 BlackHole 输入端静默。
**修复**：每请求新开输出流（已内置）；或 `launchctl kickstart -k gui/$(id -u)/com.moss.ttsd`

### greedy 采样模式 18x 劣化
**症状**：`sample_mode="greedy"` 短句合成 50.4s vs fixed 2.8s。
**修复**：使用 `sample_mode="fixed"`（已内置）。greedy 在 macOS x86_64 ORT 走慢速内核。

### 多守护进程实例风暴
**症状**：日志可见多次"加载引擎"互相覆盖；3+ 实例抢 socket/音频流。
**修复**：ttsd.py 内置 flock 单实例互斥（第二实例自动退出）。

### 偶发 AR 过生成
**症状**：个别请求合成时长远超文本合理长度（实测一次 6.5s 合成出 24.7s 音频，复测消失）。
**现状**：MOSS 自回归模型的偶发长尾，`max_new_frames=375` 帧上限兜底，不阻塞使用。若频发，检查文本是否含异常字符/无标点长串。

### 播放开头卡顿 / 合成 RTF 间歇性退化 6-14 倍（LaunchAgent QoS，未完全定位）
**症状**：daemon 里流式块产出间隔 ~1s（正常 ~0.15s），RTF 0.17→1.5-3.0 波动，卡顿时 CPU 多核满转（300%+）。独立进程跑同一合成代码完全正常（RTF 0.17-0.2，20/20）。
**已排除**：系统负载、thermal（pmset -g therm 无警告）、内存（59% free）、代码路径（MossEngine 直测与 daemon 同代码）、QoS 数值（已显式设 USER_INITIATED，PRI 37/31 正常，仍慢）。
**定位工具**：`taskpolicy -c background .venv-moss/bin/python /tmp/bench_stream_rtf.py` 可在终端稳定复现同症状（RTF 3.0 + ORT mutex crash），是判别基准。
**缓解（三选一）**：
1. `config.toml` 设 `streaming_first_audio = false` 回整段模式（整段 RTF 0.169 稳定，无流式饥饿；首帧变慢但无卡顿）——最可靠。
2. 重启 daemon（kickstart）有时恢复——间歇性，不可依赖。
3. 待深挖：sudo powermetrics 看 P/E 核分配；Instruments attach daemon。root 级工具当前受限。
**进展**：QoS 已显式 USER_INITIATED（ttsd.py 进程内 ctypes，PRI 37/31 正常）；流式 decode budget 已调优（首块 1 帧保首音，后续 4/8/16 快速建缓冲）。

### USB 声卡硬件噪音（电流声/爆破音）
**症状**：内置扬声器干净但 USB 耳机有杂音。
**结论**：USB 声卡硬件问题，与 TTS 软件无关。听朗读用内置扬声器。

## 自测（T1–T5，fail-closed）

```bash
cd scripts && .venv-moss/bin/python selftest.py
```

| 测试 | 验证内容 | 通过判据 |
|---|---|---|
| T1 | say 兜底引擎合成（**不覆盖 MOSS 生产路径**） | WAV 有效、非静音 |
| T2 | BlackHole 输出通路 | 写入无异常 |
| T3 | BlackHole 输入通路 / TCC | 收到真实回调且 callback 无错误标记；电平如实上报（dBFS 进报告），不做硬门禁 |
| T4 | 端到端回环 | 互相关检测到信号 |
| T5 | 延迟实测 | 3 档 p50_ms 数值物理自洽：0<p50≤200ms、p50 ≈ blocksize 缓冲周期整数倍、同档重复极差 ≤1ms、随 blocksize 单调不降 |

| T6 | MOSS 生产路径硬门禁（去长度偏置） | 时长 <29.95s、RMS ≥−60 dBFS、有声音频 ≥0.4s |
| T7 | 切分层不变量（零合成） | 任何返回 chunk 去标点后非空（守护标点-only 孤儿块修复） |

结果写 `scripts/selftest_report.json`。T3–T5 依赖 T3 通路；报告里任一失败即 overall=fail。T6/T7 不依赖 BlackHole。

**抖动验收（独立于 selftest，需 K×n 次合成）**：`tools/verify_render_stability.py` —— 配对 σ_render 相对门禁
（同句集、同仪器 YIN 40ms/10ms@16kHz；K=16×n=3 时要求降幅 ≥40% 且不过 1.5× 非劣性守卫），基线 σ_render=1.08 半音（df=24）。
不用句间 F0 SD：合成侧跨句离散（1.54–1.85 半音）已小于自然人声（2.68 半音），该口径判不出用户抱怨的抖动。
绝对阈值不可用——本机穷举 42 个自然语音文件无「同说话人重复同句」样本。

闭环 CER 验证（合成路径改动后的语义等价回归）：

```bash
cd scripts && .venv-moss/bin/python tools/verify_tts_cer.py                 # 默认 nonstream vs stream 对比，n=3
.venv-moss/bin/python tools/verify_tts_cer.py --modes stream --repeats 5   # 只测流式 / 加密重复
```

依赖 faster-whisper + opencc（setup.sh 已含）与 faster-whisper-base 模型（`scripts/models/faster-whisper-base`，缺失见 `models/README.txt` 从 hf-mirror 下载）。判据：对比模式逐句中位 CER 双方 < 0.15 且 |差| < 0.10；合成是采样模型，绝对 CER 波动属正常，看模式间相对差异。

## 验证收音（等价于 Zoom/微信收音）

```bash
sox -t coreaudio "BlackHole 2ch" -r 48000 -c 2 /tmp/bh.wav trim 0 9 &   # 先起录音
./scripts/run.sh "你好，世界"                                            # 再朗读
sox /tmp/bh.wav -n stat 2>&1 | grep RMS    # RMS≈0.06–0.14 即收到语音
```

## 模型矩阵

| 引擎 | 中文 | 英文 | 许可 | 模型大小 | 状态 |
|---|---|---|---|---|---|
| **MOSS**（默认）| ✅ 原生 | ✅ 原生 | Apache-2.0 | ~730MB（自动下载） | ✅ 活跃 |
| say（macOS）| ✅ 基础 | ✅ | 系统自带 | 0 | 兜底 |

## 合规边界

- MOSS xiao_ya 声音 = Non-commercial → **仅个人使用**
- 不得用于未经同意向会议/电话注入语音
- 对外分发需满足：中国深度合成标识 + EU AI Act Art.50 + 美国 robocall 规则
- 建议启用 AudioSeal 水印（对外/服务版）
