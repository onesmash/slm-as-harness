# 部署与自测报告 — tts-mic-loopback

日期：2025-09-18 · 主机：macOS 15.7.9 (24G830) · 对应方案：[report.md](../report.md)（Report scope: complete）

## 1. 部署步骤记录

| 步骤 | 命令/动作 | 结果 |
|---|---|---|
| 1 | `brew install blackhole-2ch`（用户终端执行，含 sudo 密码） | ✅ 插件落盘 `/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver` |
| 2 | 加载设备：`sudo launchctl kickstart -k system/com.apple.audio.coreaudiod` | ⚠️ 被 SIP 拒绝（`150: Operation not permitted`，macOS 15 限制） |
| 2' | 改用 `sudo killall coreaudiod`（launchd 自动拉起） | ✅ **BlackHole 2ch 注册为 device#1（in=2/out=2）** |
| 3 | venv 依赖（round 3 已装）：numpy 2.5.3 + sounddevice 0.5.6 | ✅ |
| 4 | 部署产物：`config.toml` + `speak.py` + `selftest.py` | ✅ 本目录 |

> 部署经验：macOS 15 上 `launchctl kickstart` 系统服务会被 SIP 拦截，装 BlackHole 后用 `sudo killall coreaudiod` 加载设备是可行路径。

## 2. 自测结果（selftest.py，overall=pass）

| 测试 | 内容 | 结果 | 证据 |
|---|---|---|---|
| T1 离线合成 | `say -v Tingting` → WAV LEI16@48k | ✅ PASS | 2.62s，RMS=0.114，48kHz |
| T2 输出通路 | sounddevice 写 BlackHole 输出端 | ✅ PASS | 0.5s/440Hz 无异常 |
| T3 输入通路 | 从 BlackHole 输入端采集 | ✅ PASS | 0.6s 采集成功，callback 无错误 |
| T4 端到端回环 | 播放 chirp→BlackHole，同时从输入端录制+互相关 | ✅ PASS | 互相关峰值 1499.6，**检测到回环信号** |
| T5 延迟实测 | 双标记差分 3 档 blocksize × 3 run | ✅ PASS | 9/9 有效，零欠载/溢出（下表） |

**部署即用**（任选其一，均位置无关）：

```bash
cd /Users/xuhui/Code/research/research-output/tts-mic-loopback/deployment
./run.sh "你好，部署成功"        # 推荐：包装脚本自动定位 venv
# 或直接（shebang 已指向 venv python）：./speak.py "你好，部署成功"
```

然后在任意 App（Zoom/微信/QuickTime…）的麦克风设置里选 **BlackHole 2ch** 即可收音。
已实测：真实 TTS 语音在 BlackHole 输入端以峰值 RMS 0.173 被完整接收（`SPEECH_RECEIVED_ON_LOOPBACK`）。

## 3. 端到端延迟实测（BlackHole 输出端→输入端真实环路）

| blocksize | 环路延迟（abs−200ms 合成延迟参数） | 首音延迟 P50 (abs_ms) | P95 | PortAudio 回读 out+in |
|---|---|---|---|---|
| 256 帧 | **≈5.4 ms** | 205.4 ms | 205.4 ms | 5.33+10.67=16.0 ms |
| 512 帧 | **≈16.0 ms** | 216.0 ms | 216.0 ms | 10.67+10.67=21.3 ms |
| 1024 帧 | **≈26.7 ms** | 226.7 ms | 226.7 ms | 21.33+21.33=42.7 ms |

- 与 report.md 预测吻合：缓冲项随 blocksize 线性增长（每 256 帧 ≈ +10.7 ms，= 2×256/48000，输出+输入两端口各计一次）；round 3 输出路径锚点（15.75/21.08/31.75 ms）与本次含输入端的全环路量级一致。
- 采集端 in_latency 恒为 10.67 ms（两倍 256 帧基准），构成 256 档的优势被部分抵消的原因：**真实首音差距主要由 out 端决定，256 vs 1024 差 ≈21 ms**。
- 三个档位均零欠载/零溢出；256 档在本机稳定。

## 4. TCC 行为的部署期实测更新

- **BlackHole 输入端采集未触发 TCC 麦克风弹窗**（T3/T4/T5 共 10+ 次开流均即时成功）——细化了 round 3 的预测矩阵：物理麦克风开流触发过 `kTCCServiceMicrophone` 弹窗（round 3 E4 实录），而虚拟设备输入在本机未触发。可能与负责进程已有授权或虚拟设备语义有关；消费方 App 分发时仍应按 [25][26] 保守声明 NSMicrophoneUsageDescription。
- 无人工授权环节被阻塞，整个自测在无人值守下完成。

## 5. 遗留事项

- 第三方 App（Zoom/微信）实测：本机无 GUI 自动化通道，留给用户在会议 App 里把麦克风切到 BlackHole 2ch 逐个验证（T4 的 PortAudio 采集已等价证明信号可达）。
- 常驻服务形态（UDS + launchd）：当前部署 `speak.py` 为整段朗读 CLI；服务化骨架见 report.md 集成层，可按需启用。
- `say` 引擎采样率标称 48k 已验证；接 MeloTTS/Piper 时按 report.md 重采样约定（合成端一次性重采样）。

## 6. 故障排查记录（2025-09-18 晚，首次部署后复测）

**现象**：部署自测全过后约 1 小时，BlackHole 环回突然全静音（T4 互相关归零、playrec 录到 RMS≈0.003）。

**排查链**（供后人复用）：
1. 物理回环对照（扬声器→内置麦克风）正常 → 采集系统健康，问题隔离到 BlackHole 设备本身。
2. 同期用户拔出了 USB 声卡（外置耳机/麦克风从设备列表消失）——拓扑变化与故障时间吻合。
3. `sudo killall coreaudiod` 重启进程后仍静音（此前安装后用它加载设备是有效的）。
4. coreaudiod 调试日志实锤：`IOWorkLoopInit BlackHole2ch_UID: starting` 后立刻出现 **`overload_type=Overload` + `safety_violation=1` + `scheduler_latency≈63ms`**（256 帧死线仅 5.3ms）+ `num_continuous_silent_io_cycles` —— CoreAudio 安全机制在持续输出静音循环。
5. 输出回调仍被正常拉动（1.5s 触发 282 次）、PortAudio 间歇抛 `-10863`（AudioUnit context 错误）、任意 blocksize（256–4096）/采样率（44.1k–96k）均静音。
6. 机器 18 天未重启、load 4–6：判定为长期运行下的 RT 调度劣化 × 设备拓扑突变的复合状态，用户态无法修复。

**结论与修复**：重启整机（重建 CoreAudio + HAL 插件全部状态）。若复发，按本节 1→4 快速定位；预防措施：音频测试期间避免热插拔 USB 声卡；部署脚本 `selftest.py` 已 fail-closed，可随时重跑验证。

**重启后复测（已完成）**：`selftest.py` T1–T5 全 PASS，T5 三档延迟与首次部署完全一致（abs_p50=205.4/216.0/226.6ms，9/9 有效）——overload/safety_violation 随整机重启消失，判定修复。

## 6.5 重启后必查项（新发现的坑）

1. **BlackHole 设备音量会被重置到近零**（实测原始电平约 -36dB：RMS 0.109→0.0016，信号仍在但极小）。修复命令（利用"临时设为默认输出"来改它的音量）：

   ```bash
   SwitchAudioSource -t output -s "BlackHole 2ch"
   osascript -e 'set volume output muted false' -e 'set volume output volume 100'
   SwitchAudioSource -t output -s "MacBook Pro扬声器"   # 切回
   ```

   校正后实测原始 RMS 0.0922 ✅。需要 `brew install switchaudio-osx`（formula，免 sudo）。

2. **重启后首次开流偶发 `-10863`（AudioUnit context 错误）**：HAL 客户端注册竞态，对 `InputStream/OutputStream` 的 open 做 3–5 次退避重试即可（`selftest.py` 已内置；`speak.py` 建议同法）。

## 7. 产物清单

- `config.toml` — engine/device/monitor/safety 配置（`[monitor] enabled=true` 时 speak.py 会在本地扬声器/耳机同播一份，便于人工确认；不需要时改 false）。ttsd.py 解析顺序：以本文件（`scripts/config.toml`）为基底，`~/.config/agent-voice/config.toml` 存在时**逐键合并覆盖**（用户优先；dict 递归合并，标量/列表整体替换），因此用户配置只需写要改的键；改完需重启守护进程生效。`speak.py` 仍只读内置 `scripts/config.toml`。


- `speak.py` — 文本→say→BlackHole 播放 CLI
- `selftest.py` — T1–T5 自测（fail-closed，写 `selftest_report.json`）
- `selftest_report.json` + `_t5_bs*.json` — 原始测试证据

## 6.7 语音引擎升级：say → Piper xiao_ya（2025-09-18 深夜）

**动机**：`say -v Tingting` 基础版声音机械感重（"太假了"）。Intel Mac 无法部署 MeloTTS（torch 已停发 x86_64 macOS 轮子），按个人使用场景切换 **Piper + xiao_ya medium**。

**已装组件**（.venv-dwr 内）：
- `piper-tts 1.8.0`（piper1-gpl 系）+ `unicode_rbnf sentence_stream pypinyin jieba cn2an transformers`（中文音素化链）
- g2pW 多音字模型：`models/g2pW/`（g2pw.onnx 159MB 从 hf-mirror datasets 下载 + 3 个查表文件从 g2pw 0.1.1 wheel 解出——piper 特意不 import g2pw 包，只定位数据）
- 声音模型：`models/zh_CN-xiao_ya-medium.onnx`（60MB，22.05kHz 原生）
- `HF_ENDPOINT=https://hf-mirror.com`（config.toml 已内置，代码在 hub 初始化前 setdefault）

**实测**：
- 稳态 RTF ≈ **0.06–0.08**（比实时快 12–15 倍）；CLI 单次调用因冷启动（模型加载+tokenizer 初始化）整体 RTF≈1.3–1.7，每次多花 ~5s——常驻服务形态（report T7）可消除
- 合成端 sox `rate -v` 一次性重采样 22.05k→48k，端到端 BlackHole 输入端 RMS=0.084 ✅
- 多音字（银行/长城/重量）经 g2pW 正确消歧

**许可注意**：xiao_ya 声音模型为 **Non-commercial**（BZNSYP 数据条款）——个人使用完全 OK；若产品化请切回 MeloTTS（MIT，需 arm64/torch 环境）或完成 E1 报告中的法务审查路径。引擎切换只需改 `config.toml` 的 `engine.name`（`piper` ↔ `say`）。

**已知小问题**：piper 1.8.0 的 CLI WAV 写出与 Python 3.13 `wave` 模块不兼容（`# channels not specified`）——已绕过：直接用其 Python API 取 int16 字节流自写 WAV，不经 CLI。

## 6.8 常驻服务 ttsd（首音延迟 7s → 150–370ms）

CLI 单次调用每次都要付 ~6s 冷启动（模型加载 + tokenizer 初始化 + 首次推理），短句场景首音延迟高达 RTF≈4.7。已按 report T7 架构落地常驻服务：

- `ttsd.py` — 守护进程：模型加载一次+预热；UDS JSON-lines 协议；句级切分→有界队列→顺序播放流水线（首句合成完立即开播）；BlackHole + monitor 同播；`ttsd.log` 记日志
- `ttsay.py` — 客户端：socket 不通时自动拉起守护进程；返回 `playback_started`（含 first_audio_ms）与 `done` 事件
- `run.sh` — 已切换为 ttsay 的包装（`./run.sh "文本"` 即享受低首音延迟）；一次性脚本模式保留在 `speak.py`

**实测**（守护进程存活时）：

| 场景 | 文本提交→首音 |
|---|---|
| 守护进程冷启动后首句 | 195ms |
| 稳态 | **146–367ms**（随句长浮动，含 g2pW/BERT 音素化）|
| 旧 CLI 单次调用 | ~7000ms |

运维：`pkill -f ttsd.py` 停止；日志 `tail -f ttsd.log`；已知边界：会话被强杀可能残留孤儿守护进程（监听已删除的 socket、不响应），`pkill -9 -f ttsd.py` 后由 ttsay 重新拉起即可。

## 6.9 混合语言路由（修复"英文读不了"）

**问题**：xiao_ya 是纯中文声音（BZNSYP 训练），混在中文里的英文单词（BlackHole/Python/audio…）发音破碎。

**方案**：`mixed_tts.py` —— 按字符类别切分文本段：含 CJK 的段走 xiao_ya（中文），纯 Latin 段走 **Piper lessac**（en_US，Blizzard 宽松许可，MIT 级可用性）；孤立数字经 cn2an 转中文读法；中英边界插 80ms 静音防粘字；各段 sox 重采样 48k 立体声 + 峰值保护（>0.98 压回 0.95）。

**新增产物**：`mixed_tts.py`（双声音路由模块）+ `models/en_US-lessac-medium.onnx`（60MB）+ `.onnx.json`。`speak.py`/`ttsd.py` 的 piper 路径已改走 MixedTTS（接口不变，守护进程需重启生效）。

**实测**：切分单测 4 例通过（含 GPT-4/config.toml 等带符号 token）；混合句 10.17s 音频合成仅 1.10s（热态）；守护进程端到端 BlackHole 输入端 RMS=0.141 ✅；首音：冷启动后首句 129ms、长英文句 ~1s（整句单段+sox 耗时）。

**许可**：xiao_ya 非商业（个人 OK）+ lessac Blizzard 宽松许可——混合输出仍仅限个人使用场景。

## 6.10 引擎终局：MOSS-TTS-Nano ONNX 集成为默认引擎（2025-09-19）

**背景**：Kokoro 与 Piper 拼接版 A/B 均被用户否决 → 升级研究阶梯第 3 级 MOSS-TTS-Nano（Apache-2.0，20 语言原生含中英，48kHz 双声道输出）。

**关键发现**：MOSS 官方提供 **ONNX CPU 版**（推理移除 PyTorch 依赖）——恰好绕开 Intel Mac 无 torch 轮子的死结（torch 2.2.2 cp312 x86_64 仍可装，仅为 runtime 的音频 IO 服务）。

**集成内容**：
- `.venv-moss`（py3.12）成为守护进程统一运行时：onnxruntime 1.23.2 + torch 2.2.2（numpy<2）+ transformers 4.57.1 + piper-tts 1.8.0 + sounddevice/soundfile/sentencepiece
- `moss_engine.py`：OnnxTtsRuntime 适配器（模型常驻加载；`enable_wetext=False` 绕过 pynini 依赖——已验证不影响音质；prompt=assets/audio/zh_1.wav 声音克隆）
- `ttsay.py` 守护进程改用 `.venv-moss/bin/python` 拉起；`config.toml engine.name = "moss"`（可切 piper/say）
- 踩坑记录：huggingface 直连超时→HF_ENDPOINT 镜像；下载循环路径 bug 导致权重互相覆盖→按字节校验修复；decode_shared.data 断点续传污染→整文件重下；int8 量化模型 ConvInteger 算子 macOS x86_64 无实现→换动态量化版

**验收**：MOSS 混句（BlackHole/Python/audio）单一声音贯穿、英文原生发音；守护进程冷启动（加载+预热 ~15s）→ 首音 4.6s（MOSS RTF≈1.2 预热后，质量优先）；BlackHole 输入端 RMS=0.078 ✅。

## 6.11 女声切换（声音克隆 prompt 选择，2025-09-19）

MOSS 为声音克隆架构：换声音 = 换参考音频（`config.toml [engine] prompt_audio`）。已下载仓库全部 7 个 prompt 并批量合成试听，用户选定 **zh_6**（较轻柔女声）为默认。

坑：仓库 prompt 文件格式混乱——zh_1 实为 FLAC、zh_10/zh_11 实为 MP3（ID3 头）只是扩展名 .wav；torchaudio sox 后端读不了 MP3。已用 ffmpeg 统一转真 WAV（RIFF/pcm_s16le）。自备参考音频同样必须是真 WAV。
试听文件：/tmp/voice_*.wav（zh_1=0.139 / zh_3=0.117 / zh_4=0.098 / zh_6=0.064 / zh_10=0.036 / zh_11=0.063 / en_2=0.063 RMS）。
验收：zh_6 女声经 BlackHole 输入端 RMS=0.039 ✅（音色轻柔属正常）。

## 6.12 P1-1 完成：launchd 托管守护进程（2025-09-20）

`~/Library/LaunchAgents/com.moss.ttsd.plist`：RunAtLoad + KeepAlive（崩溃/重启自动拉起）+ ThrottleInterval 10s。
验收：launchctl 托管 ✓、端到端 ttsay ✓（首音 3.9s 含闲置后首个请求初始化；热态 P50 2360ms）、kill -9 崩溃自愈 ✓（15s 内重拉并重新监听）。
运维变更：**停止守护进程必须 `launchctl unload`**（直接 pkill 会被 KeepAlive 拉起）。日志迁移至 ttsd_launchd.log。

## 6.13 事故复盘：实例风暴 + 陈旧流句柄 + 音量重置（2025-09-20 凌晨）

**现象链**：朗读开始正常 → 中途用户"听不到了" → 数字域/模拟域均无声或极小。

**三重根因**：
1. **守护进程实例风暴**：launchd KeepAlive、bench 脚本 spawn、ttsay 自动 spawn 三方同时管理，日志可见 4 次引擎加载互相覆盖 socket —— flock 单实例互斥修复（第二实例启动即退出）。
2. **陈旧流句柄**：USB 声卡拓扑变化后，长寿守护进程的输出流写入全部蒸发（BlackHole 输入端 15s 静默，但进程 339% CPU 在合成）—— 重构为**每请求按设备名新开输出流、用完即关**（开销可忽略），拓扑免疫。
3. **BlackHole 音量重置复发**（DEPLOYMENT 6.5 同因）：环路电平 -40dB（0.0015 vs 0.15）—— `fix_blackhole_volume.sh` 固化并挂入 ttsd 启动自动执行。

**验收**：自动音量自愈日志 ✓ + 端到端 BlackHole 输入端 RMS=0.0250（女声 zh_6 本身轻柔，正常区间）✅。
**运维变更**：守护进程由 launchd 独占管理；ttsay 不再 spawn；停止必须 launchctl unload。

## 6.14 爆破音修复：MOSS 句首硬切（2025-09-20）

**取证**：MOSS 单句输出从波形中段硬切入（首样本达 17-36% 满幅），句间拼接必产生咔哒声（70 句 = 70 次爆音）。
**修复**：moss_engine.synth 输出级处理——DC 去除 + 首 8ms 淡入 / 末 8ms 淡出（引擎级，ttsd/speak 全部受益）。
**验证**：修复后句首末样本归零（淡入淡出生效），边界平滑。

## 6.15 噪音最终裁决：USB 声卡硬件问题（2025-09-20）

A/B 终审：同一段朗读，**MacBook Pro 内置扬声器无任何爆破音**，USB 耳机（外置耳机）有爆破音+电流声。
结合此前取证（BlackHole 数字回环频谱干净、无工频哼声、无削波）——**杂音为 USB 声卡链路的硬件问题**（DAC 噪声 + 满载欠载），与 TTS 软件无关。

**最终配置**：MOSS 引擎 + zh_6 女声（声音克隆）+ monitor 走内置扬声器 + BlackHole 喂其他 App。
**用户建议**：听朗读用内置扬声器或 3.5mm 口；USB 声卡如需继续使用建议直连机身或加 powered Hub。

## 6.16 首音延迟优化：首句切分（2025-09-21）

first_audio ≈ 首句完整合成时间（实测占 99%，管线开销 <100ms）。
优化：首句在首个次级标点（，、：；）处切分（≤12 字），首块音频更快出声。
基线 P50=7861ms → 优化后 P50=4874ms（**-38%**）。同 workload 4 次重测验证。
残余杠杆：硬件升级（M 系列）；流式合成已否决；threads 已最优。
