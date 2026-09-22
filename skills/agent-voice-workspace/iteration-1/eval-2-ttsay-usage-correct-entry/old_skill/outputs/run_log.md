# eval-2 · ttsay 正确入口朗读 — 执行记录

- 日期：2026-09-22
- 文本：`优化后的技能测试成功`
- 结果：✅ 朗读成功，并确认播放真正完成（守护进程输出流正常关闭）

## 1. 依据的 skill 指南

先阅读 `skills/agent-voice-workspace/skill-snapshot/SKILL.md`（agent-voice skill 的一个版本）。
其「### 4. 朗读文本」一节给出的正确入口为：

```bash
./scripts/ttsay.py "要朗读的文本"
```

即 skill 目录下的 `scripts/ttsay.py`（ttsd 常驻服务客户端，只连 Unix socket `~/.config/agent-voice/ttsd.sock`，不 spawn 守护进程）。

## 2. 执行前状态检查（只读）

| 检查 | 命令 | 结果 |
|---|---|---|
| launchd 服务 | `launchctl list \| grep -i moss` | `60643  -15  com.moss.ttsd`（PID 60643 运行中） |
| 守护进程 | `ps aux \| grep ttsd` | `.../Python .../scripts/ttsd.py`（PID 60643，11:10AM 启动） |
| socket | `ls ~/.config/agent-voice/` | `ttsd.sock` 存在 |

## 3. 使用的确切命令

工作目录：`/Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice`

```bash
./scripts/ttsay.py "优化后的技能测试成功"
```

（未使用 venv 前缀——ttsay.py 仅依赖 Python 标准库 json/pathlib/socket/sys/time，且 SKILL.md 的用法即为直接执行脚本。未重装依赖、未重启/改动 launchd、未改任何配置。）

## 4. 客户端实际输出的事件行

```
[ttsay] 🔊 开始播放（文本提交→首音 514.6ms）
[ttsay] 完成：音频 2.72s / 合成 0.51s / 1 句
```

退出码 `0`。事件流顺序：`playback_started`（首音延迟 514.6ms）→ `done`（音频 2.72s / 合成 0.51s / 1 句），ttsay.py 收到 `done` 即代表本次朗读播放结束。

## 5. 完成性的交叉佐证（守护进程侧日志）

`~/.config/agent-voice/ttsd.log` 尾部：

```
[ttsd 11:14:20] 客户端接入
[ttsd 11:14:20] 客户端接入
[ttsd 11:14:25] 本请求输出流已关闭（monitor 为每句新开，无句柄过期问题）
```

时间线吻合：11:14:19 提交请求 → 11:14:20 首音（客户端报 514.6ms）→ 播放 2.72s → 11:14:25 守护进程关闭本请求输出流。播放确实完整结束，非中途截断。

## 6. 遇到的障碍

无。首次调用即成功，未触发排障路径。过程中未进行任何重装、launchd 操作或配置修改。
