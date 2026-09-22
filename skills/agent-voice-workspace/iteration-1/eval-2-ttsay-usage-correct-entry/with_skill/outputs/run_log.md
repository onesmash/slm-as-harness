# agent-voice 真实朗读执行记录（eval-2 / with_skill）

- 日期：2026-02-13
- 目标文本：`优化后的技能测试成功`
- 系统：macOS，MOSS-TTS-Nano 本地合成 → BlackHole 2ch 虚拟麦克风输出（monitor 同播可听）

## 0. 约束遵守

- 未重装依赖、未重启/卸载/改动 launchd 服务、未修改任何配置。
- 仅只读检查（目录列表、`pgrep`、`launchctl print`、读脚本源码）+ 一次朗读调用。

## 1. 调用方式依据（SKILL.md）

先阅读 `skills/agent-voice/SKILL.md`，「朗读文本」一节推荐：

```bash
./scripts/run.sh "要朗读的文本"          # 推荐：run.sh 自动用 .venv-moss 的 python
```

调用约定：脚本 shebang 是 `#!/usr/bin/env python3`，依赖装在 `.venv-moss`——
**始终通过 `run.sh` 或显式 `.venv-moss/bin/python` 调用**，不要直接 `./ttsay.py`。
`run.sh` 内容（实读确认）：`exec "$DIR/.venv-moss/bin/python" "$DIR/ttsay.py" "$@"`，即走常驻 ttsd 客户端。

`ttsd.py` 源码确认（只读）：`done` 事件在播放线程阻塞消费完全部合成音频之后发送，
因此客户端打印「完成」即代表朗读真正播放完毕，可作为完成判据。

## 2. 前置状态检查（只读）

```
$ pgrep -fl ttsd.py
60643 /Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts/ttsd.py

$ launchctl print gui/$(id -u)/com.moss.ttsd
state = running
pid = 60643
job state = running
```

守护进程经 launchd（com.moss.ttsd）常驻运行中，pid 60643。

## 3. 执行的确切命令

```bash
cd /Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice
./scripts/run.sh "优化后的技能测试成功"
```

（等价展开：`.venv-moss/bin/python ttsay.py "优化后的技能测试成功"`，
通过 `~/.config/agent-voice/ttsd.sock` 把文本发给常驻守护进程 ttsd.py。）

## 4. 客户端实际输出的事件行（stdout 原样）

```
[ttsay] 🔊 开始播放（文本提交→首音 452.8ms）
[ttsay] 完成：音频 2.24s / 合成 0.45s / 1 句
[exit code: 0]
```

对应守护进程 JSON 事件流：
- `{"event": "playback_started", "first_audio_ms": 452.8}`
- `{"event": "done", "audio_seconds": 2.24, "synth_seconds": 0.45, "sentences": 1}`

## 5. 完成确认

- ✅ 收到 `playback_started`：文本提交 → 首音 452.8ms（Apple Silicon 热态基线 418–449ms 附近，正常）。
- ✅ 收到 `done`：音频 2.24s，合成 0.45s，1 句。音频时长与 10 字中文短句合理长度匹配
  （无 AR 过生成长尾）；`done` 在播放线程消费完全部音频后发出 → 朗读真正播放完成。
- ✅ 客户端进程退出码 0，收到 done 后正常退出（守护进程保持常驻）。

## 6. 结论

朗读**成功**：MOSS 引擎合成 2.24s 音频，经 BlackHole 2ch 虚拟麦克风流式输出、
monitor 同播本地可听（本次运行实际有声音输出一次），播放完整结束。
