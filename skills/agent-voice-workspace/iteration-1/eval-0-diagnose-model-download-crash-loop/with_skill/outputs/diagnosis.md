# 诊断报告：TTS 守护进程崩溃重启循环（模型下载 401 → FileNotFoundError）

- 场景：按 agent-voice skill 部署的 macOS TTS 守护进程（launchd `com.moss.ttsd`）反复崩溃重启，朗读无声
- 依据：`skills/agent-voice/SKILL.md`「已知问题与修复」第一节「模型下载静默失败：hf-mirror 不支持 Xet 协议」；辅证 `scripts/moss_engine.py:29-31`
- 性质：本报告仅为诊断，未对系统做任何修改

## 一、根因

**huggingface_hub ≥ 1.0 默认启用 Xet 存储协议，而 hf-mirror 只代理经典 HTTP 下载通道，不支持 Xet 的 CAS 协议。**

MOSS-TTS-Nano 的模型仓库（`OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX`、`OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX`）的大文件（onnx/data）以 Xet 格式存储。下载时 huggingface_hub 会按文件元数据里给出的 Xet 端点，直接向 `cas-server.xethub.hf.co` 发起 reconstruction 请求。经 hf-mirror 镜像使用时，这个请求没有（也不可能有）对真实 Xet 服务的有效凭证，返回 **401 Unauthorized**，大文件下载任务失败：

```
RuntimeError: Task error: File reconstruction error: CAS Client Error:
Request error: HTTP status client error (401 Unauthorized),
domain: https://cas-server.xethub.hf.co/v2/reconstructions/...
```

结果是一次"静默的部分下载"：只有几个几百 KB 的非 LFS 小 json 走经典通道落盘成功，**几百 MB 的 onnx/权重文件一个都没下来**。引擎初始化时找不到必需文件，抛 `FileNotFoundError: codec_browser_onnx_meta.json` 退出；launchd 的 KeepAlive 又把它拉起 → 再次失败 → 形成**崩溃重启循环**，引擎从未加载成功，因此朗读完全没有声音。

agent-voice 当前代码已内置修复——`scripts/moss_engine.py` 在创建引擎前设置了：

```python
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")   # 强制走经典 HTTP 通道
```

本机仍然 401，说明**修复在这台机器上没有生效**，按优先级排查：

1. 部署到 launchd 的脚本/引擎是**修复合入之前的旧版本**（最常见）；
2. 守护进程环境里已有 `HF_HUB_DISABLE_XET=0`（或被 plist 的 `EnvironmentVariables` 覆盖）——注意代码用的是 `setdefault`，外部已设值时**不会覆盖**；
3. 首次下载已经留下**残缺的 models 目录**，即使修复生效也需要补齐/重下才能恢复。

## 二、为什么日志呈现这些现象

| 现象 | 解释 |
|---|---|
| `RuntimeError: Task error: ... cas-server.xethub.hf.co ... 401` | Xet 协议的下载在 huggingface_hub 内部以并发 task 执行；对 CAS 服务的 reconstruction 请求鉴权失败（mirror 场景无真实 Xet 凭证），任务级报错向上抛出 |
| 随后 `FileNotFoundError: codec_browser_onnx_meta.json` | 401 中断了 snapshot_download，只有非 LFS 小文件落盘；运行时初始化按清单逐个打开模型文件时找不到必需文件 |
| models 目录只有两个几百 KB 的 json、没有 onnx | 正是"部分下载"的直接证据：小 json 走 hf-mirror 经典 HTTP 通道成功；大文件（Xet 存储）全部失败 |
| 守护进程反复崩溃重启 | plist 带 KeepAlive，进程因未捕获异常退出后被 launchd 无限拉起，每次重走"尝试下载→401→缺文件→退出" |
| 朗读没声音 | 引擎从未完成初始化，没有任何音频到达 BlackHole |
| 网络明明是通的（brew 正常） | 故障与通用连通性无关：brew 走的是另一条链路；这里失败的是 hf-mirror 不支持的 Xet 协议通道，属于**协议层 401**，不是断网 |

## 三、修复步骤（可复制命令）

### 第 1 步：确认内置修复是否存在且未被环境覆盖（只读检查）

```bash
cd /Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts

# 1) 引擎代码里应有这两行 setdefault
grep -n "HF_HUB_DISABLE_XET\|HF_ENDPOINT" moss_engine.py

# 2) 当前 shell 与 launchd 环境里是否有人把它设成了 0/未设
echo "shell: HF_HUB_DISABLE_XET=${HF_HUB_DISABLE_XET:-<unset>}"
launchctl print gui/$(id -u)/com.moss.ttsd | grep -i -E "HF_HUB_DISABLE_XET|HF_ENDPOINT" || echo "launchd 未显式设置（正常）"

# 3) 已安装的 plist 是否注入了覆盖值
plutil -p ~/Library/LaunchAgents/com.moss.ttsd.plist 2>/dev/null | grep -i -E "XET|ENDPOINT" || echo "plist 无覆盖（正常）"
```

判定：
- 第 1 项 grep **无输出** → 部署的是旧版 `moss_engine.py`，需更新 skill/scripts 后重装守护进程（重跑 `./scripts/setup.sh`）；
- 第 2/3 项发现 `HF_HUB_DISABLE_XET=0` 或可疑覆盖 → 删除该覆盖源（shell rc / plist `EnvironmentVariables`）；
- 若三项都正常，则问题就是**残缺的模型目录**，直接做第 2 步补下载即可。

### 第 2 步：带 `HF_HUB_DISABLE_XET=1` 手动补齐两个模型（核心修复）

```bash
cd /Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts

HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
  .venv-moss/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX', local_dir='MOSS-TTS-Nano/models/MOSS-TTS-Nano-100M-ONNX')"

HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
  .venv-moss/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX', local_dir='MOSS-TTS-Nano/models/MOSS-Audio-Tokenizer-Nano-ONNX')"
```

说明：
- 全程约 **730MB**，走 hf-mirror 经典 HTTP 通道，耗时取决于带宽；不要中途判定卡死（skill 明确提示首次下载属正常流程）。
- `snapshot_download` 会自动续传/补齐缺失文件，已下好的两个小 json 不会重复下载。
- 若补下载仍报 401：说明运行时环境仍启用了 Xet（回到第 1 步找覆盖源）；兜底方案是删掉两个残缺目录后用上面同样命令整体重下（保留 `.venv-moss`，不要重装依赖）：
  ```bash
  rm -rf MOSS-TTS-Nano/models/MOSS-TTS-Nano-100M-ONNX MOSS-TTS-Nano/models/MOSS-Audio-Tokenizer-Nano-ONNX
  ```

### 第 3 步：重启守护进程加载完整模型

```bash
launchctl kickstart -k gui/$(id -u)/com.moss.ttsd
```

## 四、如何验证修复

```bash
# 1) 模型文件补齐：应能看到 onnx/data 等大文件，两个 repo 合计约 730MB（而不是只剩几百 KB 的 json）
du -sh /Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts/MOSS-TTS-Nano/models/*
find /Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts/MOSS-TTS-Nano/models -name "*.onnx" | head

# 2) 守护进程稳定常驻：不再崩溃循环（多看几次 state 都应是 running、pid 不变）
launchctl print gui/$(id -u)/com.moss.ttsd | grep -E "state|pid"

# 3) 守护进程日志不再出现 401 / FileNotFoundError（日志路径可在 plist 的 StandardErrorPath 找到）
plutil -p ~/Library/LaunchAgents/com.moss.ttsd.plist | grep -i StandardError

# 4) 实际朗读出声
/Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts/run.sh "你好，世界"

# 5) BlackHole 收音闭环验证（等价 Zoom/微信收音）：RMS≈0.06–0.14 即收到语音
sox -t coreaudio "BlackHole 2ch" -r 48000 -c 2 /tmp/bh.wav trim 0 9 &
/Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts/run.sh "验证收音测试"
sox /tmp/bh.wav -n stat 2>&1 | grep RMS

# 6) 可选：跑全套自测 T1–T5，报告写 scripts/selftest_report.json，任一失败即 overall=fail
cd /Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice/scripts && .venv-moss/bin/python selftest.py
```

通过标准：模型目录含完整 onnx（~730MB）、守护进程常驻不再重启、日志无 401/FileNotFoundError、`run.sh` 有声、BlackHole 回环 RMS 落在 0.06–0.14、selftest overall=pass。

## 五、防复发建议

- 升级/重新部署 agent-voice 后，用第 1 步的三条只读检查确认 `HF_HUB_DISABLE_XET=1` 存在于引擎代码且未被环境覆盖，再触发首次下载。
- 任何环境诊断此类问题，先查 `HF_HUB_DISABLE_XET`（skill 原文：若诊断其他环境，先查该环境变量）。
- 不要改用回退方案"升级 torchaudio/换镜像"——本问题与 torchaudio 解码（另一条已知问题）无关，且 skill 要求不要在下载中断时误判为卡死而反复重启，这只会放大 KeepAlive 循环。
