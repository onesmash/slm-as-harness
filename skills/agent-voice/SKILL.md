---
name: agent-voice
description: "在 macOS 上从零搭建'文本→本地 TTS→虚拟麦克风'系统并正确运行。当用户想要把文字转成语音并通过虚拟麦克风输出给其他应用（Zoom/微信/录音软件等）时使用此 skill。覆盖：MOSS-TTS-Nano ONNX 引擎部署、BlackHole 虚拟声卡安装与配置、launchd 常驻服务、品牌词发音映射、爆破音修复、闭环 CER 评分。即使用户只说'读一下这段文字'或'帮我搭个 TTS'，只要涉及本地语音合成输出到虚拟麦克风，就应使用此 skill。"
---

# TTS 虚拟麦克风系统 — Agent 操作指南

## 系统做什么

```
用户文本 → MOSS 本地合成 → BlackHole 2ch（虚拟麦克风）→ 其他 App 收音
                                                    └→ monitor 同播（本地可听）
```

把文字转成语音，通过 BlackHole 虚拟声卡"假装"成麦克风输入。任何 App（Zoom、微信、QuickTime…）把麦克风切到 **BlackHole 2ch** 就能收到合成语音。

## 前置条件

| 项 | 要求 | 检查命令 |
|---|---|---|
| macOS | 12+ | `sw_vers` |
| BlackHole 2ch | 已安装 | `system_profiler SPAudioDataType \| grep BlackHole` |
| Python 3.12 | .venv-moss | `python3.12 --version` |
| SwitchAudioSource | 音量自愈用 | `which SwitchAudioSource` |
| sox + ffmpeg | 音频处理 | `which sox ffmpeg` |

**安装 BlackHole**（需用户输密码）：
```bash
brew install blackhole-2ch
sudo killall coreaudiod   # 加载设备
```
⚠️ macOS 15+ 上 `launchctl kickstart` 会被 SIP 拦截，用 `killall` 替代。

## 快速部署

本 skill 的 `scripts/` 目录包含全部可执行文件。部署步骤：

### 1. 安装 Python 依赖
```bash
python3.12 -m venv .venv-moss
.venv-moss/bin/pip install numpy onnxruntime sentencepiece sounddevice soundfile \
  transformers piper-tts cn2an pypinyin pypinyin-dict jieba ordered-set
```

### 2. BlackHole 音量自愈
每次守护进程启动时自动运行（ttsd.py 内置）。手动修复：
```bash
./scripts/fix_blackhole_volume.sh
```

### 3. 启动守护进程
```bash
# 推荐方式：launchd 托管（开机自启 + 崩溃自愈）
cp com.moss.ttsd.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.moss.ttsd.plist

# 或手动启动（调试用）
./scripts/ttsd.py &
```

### 4. 朗读文本
```bash
./scripts/ttsay.py "要朗读的文本"
```

## 配置（config.toml）

```toml
[engine]
name = "moss"           # moss（质量档）| say（零安装兜底）
prompt_audio = "assets/audio/zh_6.wav"  # 声音克隆参考音频
number_normalize = true  # 数字→中文读法

[device]
name = "BlackHole 2ch"
blocksize = 256         # 实测最优（RTF 无损失）
latency = "low"

[monitor]
enabled = true           # 本地同播
```

**用户覆盖**：`~/.config/agent-voice/config.toml` 存在时，ttsd.py 以内置 `scripts/config.toml` 为基底**逐键合并**（用户优先；dict 递归合并，标量/列表整体替换），用户配置只需写要改的键，不必是完整副本。改配置后需重启守护进程生效。`speak.py` 只读内置 config.toml。

## 架构

```
文本 → cn2an 数字归一化 → 品牌词映射 → 句级切分(≤60字)
  → MOSS AR 合成（逐句流水线）→ 有界队列(4)
    → BlackHole 输出（虚拟麦克风 → 其他 App）
    → afplay 独立进程（monitor → 本地扬声器/耳机）
```

## 性能基线（Intel MBP 实测）

| 指标 | 值 |
|---|---|
| 稳态合成 RTF | 0.85–1.05（threads=2 最优）|
| 首音延迟（热态） | 150–370ms |
| 首音延迟（MOSS 长句冷启动） | 4.6–9.5s |
| BlackHole 回环延迟 | 5.4/16.0/26.7ms @ 256/512/1024 帧 |
| 守护进程冷启动 | 15–71s（模型加载+预热）|

## 已知问题与修复（全部经实测验证）

### BlackHole 音量被系统重置到近零（-40dB）
**症状**：回环录音 RMS≈0.001x（正常应为 0.09–0.14）。
**修复**：ttsd 启动时自动运行 `fix_blackhole_volume.sh`（临时切默认输出→拉满→还原）。手动：`./scripts/fix_blackhole_volume.sh`

### USB 声卡插拔后输出流句柄过期
**症状**：守护进程在合成（CPU 高）但 BlackHole 输入端静默。
**修复**：每请求新开输出流（已内置）；或 `launchctl kickstart -k gui/$(id -u)/com.moss.ttsd`

### greedy 采样模式 18x 劣化
**症状**：`sample_mode="greedy"` 短句合成 50.4s vs fixed 2.8s。
**修复**：使用 `sample_mode="fixed"`。greedy 在 macOS x86_64 ORT 走慢速内核。

### 多守护进程实例风暴
**症状**：日志可见多次"加载引擎"互相覆盖；3+ 实例抢 socket/音频流。
**修复**：ttsd.py 内置 flock 单实例互斥（第二实例自动退出）。

### USB 声卡硬件噪音（电流声/爆破音）
**症状**：内置扬声器干净但 USB 耳机有杂音。
**结论**：USB 声卡硬件问题，与 TTS 软件无关。听朗读用内置扬声器。

## 自测（T1–T5，fail-closed）

```bash
./scripts/selftest.py
```

| 测试 | 验证内容 | 通过判据 |
|---|---|---|
| T1 | say 离线合成 | WAV 有效、非静音 |
| T2 | BlackHole 输出通路 | 写入无异常 |
| T3 | BlackHole 输入通路 | 采集成功 |
| T4 | 端到端回环 | 互相关检测到信号 |
| T5 | 延迟实测 | 3 档 blocksize P50/P95 |

## 模型矩阵

| 引擎 | 中文 | 英文 | 许可 | 模型大小 | 状态 |
|---|---|---|---|---|---|
| **MOSS**（默认）| ✅ 原生 | ✅ 原生 | Apache-2.0 | 745MB | ✅ 活跃 |
| say（macOS）| ✅ 基础 | ✅ | 系统自带 | 0 | 兜底 |

## 合规边界

- MOSS xiao_ya 声音 = Non-commercial → **仅个人使用**
- 不得用于未经同意向会议/电话注入语音
- 对外分发需满足：中国深度合成标识 + EU AI Act Art.50 + 美国 robocall 规则
- 建议启用 AudioSeal 水印（对外/服务版）
