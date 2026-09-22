# 诊断报告：MOSS-TTS 守护进程崩溃重启（模型下载 401 → FileNotFoundError 循环）

- 机器现象：TTS 守护进程反复崩溃重启，朗读无声；`MOSS-TTS-Nano/models/` 下只有两个几百 KB 的 json，没有任何 onnx/data 文件；网络本身通（brew 正常）。
- 结论先行：**这不是网络故障，是 Hugging Face 下载通道协议不匹配**。`HF_ENDPOINT=https://hf-mirror.com` 镜像 + 新版 `huggingface_hub`（装有 `hf_xet`）默认走 Xet 存储协议，而 hf-mirror 不支持/不代理 Xet CAS 协议，客户端被指到真正的 `cas-server.xethub.hf.co` 时鉴权失败（401），大文件（.onnx/.data）全部下载失败，只留下先完成的小 json；引擎加载时找不到必需资产就崩溃，launchd `KeepAlive` 又不断拉起，形成崩溃循环。

## 一、根因

1. **下载入口在守护进程内**：`ttsd.py` 启动 → `Engine()` → `MossEngine(...)`（moss_engine.py）→ `OnnxTtsRuntime(model_dir=MOSS-TTS-Nano/models)` → `ensure_browser_onnx_model_dir()` 发现 `browser_poc_manifest.json` 缺失 → 自动调用 `snapshot_download` 从 `OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX` 和 `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` 下载（约 745MB）。也就是说，模型下载失败直接等于守护进程启动失败。
2. **镜像 + Xet 协议冲突（核心）**：skill 链路里 `HF_ENDPOINT=https://hf-mirror.com`（ttsd.py 从 config.toml 注入，moss_engine.py 也 setdefault）。但两个 OpenMOSS-Team 仓库是 Xet 存储后端；新版 huggingface_hub 只要装了 `hf_xet` 就默认用 Xet CAS 协议下载。hf-mirror 只镜像经典 HTTP resolve/CDN 通道，**不支持 Xet CAS**；客户端拿到的重建请求落在 `https://cas-server.xethub.hf.co/v2/reconstructions/<id>`，其携带的（经镜像签发的）凭证在该服务器上无效 → `HTTP 401 Unauthorized`。日志里的 `File reconstruction error: CAS Client Error ... 401` 就是这个。
3. **部署版本缺少修复开关**：skill 当前版本（skill-snapshot）的 `moss_engine.py` 已含修复，且注释直接记录了本故障：
   ```python
   os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
   # hf-mirror 不支持 Xet 存储协议（CAS 401）；强制走经典 HTTP 下载通道
   os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
   ```
   出问题的机器日志仍出现 CAS 401，说明 Xet 通道在下载时是活的——即**机器上实际部署的 moss_engine.py 是没有这行的旧版**（或该变量在 launchd 环境里被覆盖）。launchd plist 没有配置任何 `EnvironmentVariables`，ttsd.py 也只注入 `HF_ENDPOINT`，不注入 `HF_HUB_DISABLE_XET`，因此开关是否生效完全取决于磁盘上那份 moss_engine.py。
4. **为什么"网络是通的"不矛盾**：brew 走的是完全不同的域名与协议，只能证明出网正常；这里的问题是**鉴权 + 协议**（镜像与 Xet CAS 之间的 token 不互认），与连通性无关。若走经典 HTTP 通道（`HF_HUB_DISABLE_XET=1`），hf-mirror 是可以正常供数的——这正是 DEPLOYMENT.md 记录的踩坑路线（直连超时→切镜像）能成立的原因。

## 二、为什么日志呈现这些现象

- `RuntimeError: Task error: File reconstruction error: CAS Client Error ... 401 ... cas-server.xethub.hf.co/v2/reconstructions/...`
  → hf_xet 后台 worker 在重建大文件时被 CAS 服务器拒绝。这是"下载大文件失败"的第一现场。
- `FileNotFoundError: .../MOSS-Audio-Tokenizer-Nano-ONNX/codec_browser_onnx_meta.json`
  → `snapshot_download` 半途而废后，本地只剩下载已完成的小文件（两个几百 KB 的 json——正好是体积小、排在前面的元数据），`.onnx`/`.data` 一个都没有。运行时随后加载 codec 元数据/权重时找不到文件，抛 `FileNotFoundError`（onnx_tts_runtime.py 中 codec_meta 是必需资产，见 `_normalize_download_layout(required_names=("codec_browser_onnx_meta.json",))` 及后续 `self.codec_meta` 读取）。两条报错是同一次失败的两面：**下载 401 → 目录残缺 → 加载缺文件**。
- 模型目录只有两个 json、没有 onnx
  → snapshot_download 是逐文件下载的，失败前已完成的小文件留在磁盘上，形成"看似下载过、实则半成品"的状态。
- 反复崩溃重启
  → `Engine()` 抛异常 → ttsd 进程退出 → plist `KeepAlive=true` + `ThrottleInterval=10s` 让 launchd 每 10 秒重拉一次，每次重跑"发现缺 manifest → 尝试下载 → 401 → 缺文件 → 退出"，无限循环。`HF_HUB_DISABLE_XET` 缺失时每次重试都注定失败，而且每次都白等下载阶段，朗读自然全程无声。
- ⚠️ 附带风险：每次崩溃重拉都会重新发起下载，半成品 `.data` 若被断点续传污染会掩盖问题——DEPLOYMENT.md 已有先例（"decode_shared.data 断点续传污染→整文件重下"），修复时必须清干净再下。

## 三、修复步骤（命令可复制；本报告仅为诊断，未在机器上执行）

> 以下按 skill 默认部署路径 `~/.agents/skills/agent-voice/scripts`（见 com.moss.ttsd.plist）。若机器上路径不同，替换为实际 `scripts` 目录。

**第 0 步：确认诊断（只读）**

```bash
# 旧版应无输出/无此行；修复版含 HF_HUB_DISABLE_XET
grep -n "HF_HUB_DISABLE_XET" ~/.agents/skills/agent-voice/scripts/moss_engine.py
# 确认 hf_xet 已装（即 Xet 通道处于启用状态）
~/.agents/skills/agent-voice/scripts/.venv-moss/bin/pip show hf_xet
# 确认模型目录是半成品
ls -la ~/.agents/skills/agent-voice/scripts/MOSS-TTS-Nano/models/*/
```

**第 1 步：先停掉崩溃循环**（KeepAlive 会不断拉起，必须 unload；SKILL.md 提示 macOS 15+ 勿用 `launchctl kickstart`，会被 SIP 拦）

```bash
launchctl unload ~/Library/LaunchAgents/com.moss.ttsd.plist
```

**第 2 步：把 skill 修复版 moss_engine.py 同步到部署目录**（或至少手工补上那两行 setdefault）。双保险起见，同时把开关写进 plist：

```bash
cp /Users/hui.xu/SourceCode/slm-as-harness/skills/agent-voice-workspace/skill-snapshot/scripts/moss_engine.py \
   ~/.agents/skills/agent-voice/scripts/moss_engine.py
```

并在 `~/Library/LaunchAgents/com.moss.ttsd.plist` 的 `<dict>` 中加入环境变量（防止任何代码路径绕过 setdefault）：

```xml
    <key>EnvironmentVariables</key>
    <dict>
        <key>HF_ENDPOINT</key>
        <string>https://hf-mirror.com</string>
        <key>HF_HUB_DISABLE_XET</key>
        <string>1</string>
    </dict>
```

（更彻底的替代方案：`.venv-moss/bin/pip uninstall -y hf_xet`，让 huggingface_hub 无 Xet 可用；env 开关是 skill 认可的做法，优先用开关。）

**第 3 步：清除半成品模型目录**（防止断点续传污染，参考 DEPLOYMENT.md 踩坑记录）

```bash
rm -rf ~/.agents/skills/agent-voice/scripts/MOSS-TTS-Nano/models/MOSS-TTS-Nano-100M-ONNX \
       ~/.agents/skills/agent-voice/scripts/MOSS-TTS-Nano/models/MOSS-Audio-Tokenizer-Nano-ONNX
```

**第 4 步：前台手动重下模型**（约 745MB；前台跑失败可见，不要让守护进程在后台盲试）

```bash
cd ~/.agents/skills/agent-voice/scripts
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
.venv-moss/bin/python - <<'PY'
from pathlib import Path
from huggingface_hub import snapshot_download
base = Path("MOSS-TTS-Nano/models")
snapshot_download(repo_id="OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX",
                  local_dir=str(base / "MOSS-TTS-Nano-100M-ONNX"),
                  allow_patterns=["*.onnx", "*.data", "*.json", "tokenizer.model"])
snapshot_download(repo_id="OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
                  local_dir=str(base / "MOSS-Audio-Tokenizer-Nano-ONNX"),
                  allow_patterns=["*.onnx", "*.data", "*.json"])
PY
```

备用通道（镜像也不可用时）：`git lfs install && git clone https://hf-mirror.com/OpenMOSS-Team/<repo名>` 后把目录摆到 `models/` 对应位置——git-lfs 走经典协议，不碰 Xet。

**第 5 步：重新加载守护进程**

```bash
launchctl load ~/Library/LaunchAgents/com.moss.ttsd.plist
# 改过 plist 的话先 load 再看日志；日志在 ~/.config/agent-voice/ttsd.log
tail -f ~/.config/agent-voice/ttsd.log
```

## 四、如何验证修复

1. **日志通过冷启动**：`ttsd.log` 出现 `加载引擎...` → 约 15–71 秒后出现 `引擎[moss]就绪（加载+预热 ...s）`，且不再循环出现 401 / FileNotFoundError。注意冷启动本来就要几十秒，别误判为卡死。
2. **模型文件齐全**：
   ```bash
   ls -la ~/.agents/skills/agent-voice/scripts/MOSS-TTS-Nano/models/MOSS-Audio-Tokenizer-Nano-ONNX/
   # 应看到 codec_browser_onnx_meta.json + moss_audio_tokenizer_{encode,decode_*}.onnx + .data（共约 90MB）
   ls -la ~/.agents/skills/agent-voice/scripts/MOSS-TTS-Nano/models/MOSS-TTS-Nano-100M-ONNX/
   # 应看到 browser_poc_manifest.json、tts_browser_onnx_meta.json、tokenizer.model 及 TTS onnx/data（合计约 745MB 量级）
   ```
   判据：不再只有"两个 json"；`.onnx` 与 `.data` 均在且体积为 MB–百 MB 级。
3. **守护进程稳定**：`ps aux | grep ttsd` 进程持续存活超过 2 分钟；`launchctl list | grep com.moss.ttsd` 无频繁重启记录（上次退出码为 0 或不显示非零）。
4. **端到端朗读有声**：
   ```bash
   ~/.agents/skills/agent-voice/scripts/ttsay.py "修复验证测试。"
   ```
   其他应用把麦克风切到 BlackHole 2ch 能听到声音；`system_profiler SPAudioDataType | grep BlackHole` 设备在位。
5. **闭环自测**（skill 内置，fail-closed）：
   ```bash
   cd ~/.agents/skills/agent-voice/scripts && ./selftest.py
   ```
   判据：T1–T5 全过，尤其 T4 端到端回环互相关检测到信号；回环录音 RMS 落在正常区间 0.09–0.14（排除 BlackHole 音量被重置这一已知独立问题——若 RMS≈0.001x，跑 `./fix_blackhole_volume.sh`，那是另一类故障，与本次 401 无关）。

## 五、一句话总结

旧版部署缺 `HF_HUB_DISABLE_XET=1`，导致走 hf-mirror 镜像时仍用 Xet CAS 协议取大文件并在 `cas-server.xethub.hf.co` 鉴权 401；onnx 权重全部下载失败只留下小 json，守护进程每次启动加载缺文件即崩，launchd KeepAlive 无限重拉。修复 = 停服务 → 同步带开关的 moss_engine.py（plist 里加 env 双保险）→ 清半成品目录 → 经典 HTTP 通道重下两个 ONNX 仓库 → load 服务 → 日志冷启动通过 + selftest T1–T5 验证。
