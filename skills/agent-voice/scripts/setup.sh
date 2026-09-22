#!/bin/bash
# setup.sh — agent-voice 一键部署（前置检查 → venv → 依赖 → launchd → 自测）
#
# 用法:
#   ./setup.sh              # 全量部署
#   ./setup.sh --skip-test  # 部署后跳过 selftest
#
# 退出码: 0=成功 1=需要人工介入（按提示执行后重跑） 2=部署失败
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="$HOME/.config/agent-voice"
PLIST_LABEL="com.moss.ttsd"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
SKIP_TEST=0
[[ "${1:-}" == "--skip-test" ]] && SKIP_TEST=1

log()  { echo "[setup] $*"; }
fail() { echo "[setup] ✗ $*" >&2; exit 2; }
need_user() { echo "[setup] ⚠ 需要人工介入:" >&2; echo "$1" >&2; exit 1; }

mkdir -p "$STATE_DIR"

# ── 1. Python 3.12 ──────────────────────────────────────────────
PY=python3.12
command -v "$PY" >/dev/null 2>&1 || {
  log "python3.12 未安装，尝试 brew install python@3.12 ..."
  command -v brew >/dev/null 2>&1 && brew install python@3.12 || need_user "请安装 Python 3.12 后重跑: brew install python@3.12"
}
command -v "$PY" >/dev/null 2>&1 || need_user "python3.12 仍不可用，请手动安装后重跑"
log "Python: $($PY --version)"

# ── 2. BlackHole 2ch ────────────────────────────────────────────
BH_OK=0
system_profiler SPAudioDataType 2>/dev/null | grep -qi blackhole && BH_OK=1
if [[ $BH_OK -eq 0 ]]; then
  # brew cask 的 pkg 安装器需要 sudo 密码，agent/无终端环境必失败 → 交给用户终端执行
  need_user "BlackHole 2ch 未安装。请在你自己的终端执行（需要输密码）:
  brew install --cask blackhole-2ch
  sudo killall coreaudiod
完成后重跑 ./setup.sh"
fi
log "BlackHole 2ch: 已注册"

# ── 3. venv + 依赖 ──────────────────────────────────────────────
cd "$DIR"
if [[ ! -x .venv-moss/bin/python ]]; then
  log "创建 venv (.venv-moss) ..."
  $PY -m venv .venv-moss || fail "venv 创建失败"
fi
# torch/torchaudio/torchcodec/huggingface_hub 为 MOSS 引擎运行必需，不可省
log "安装 Python 依赖（torch 较大，首次约 2-5 分钟）..."
.venv-moss/bin/pip install --quiet --upgrade pip
.venv-moss/bin/pip install --quiet \
  numpy onnxruntime sentencepiece sounddevice soundfile \
  transformers piper-tts cn2an pypinyin pypinyin-dict jieba ordered-set \
  torch torchaudio torchcodec huggingface_hub \
  || fail "pip install 失败，查看上方 pip 输出"
log "依赖安装完成"

# ── 4. launchd 服务（plist 从模板实例化，路径随部署环境自适应）──
sed -e "s|@@VENV_PYTHON@@|$DIR/.venv-moss/bin/python|g" \
    -e "s|@@SCRIPTS_DIR@@|$DIR|g" \
    -e "s|@@STATE_DIR@@|$STATE_DIR|g" \
    "$DIR/com.moss.ttsd.plist.tmpl" > "$PLIST_DST" || fail "plist 生成失败"
launchctl unload "$PLIST_DST" 2>/dev/null
launchctl load "$PLIST_DST" || fail "launchctl load 失败"
log "launchd 服务已加载: $PLIST_DST"

# ── 5. 等待守护进程就绪（首次会自动下载模型 ~730MB，走 hf-mirror）──
log "等待守护进程就绪（首次启动需下载 MOSS 模型 ~730MB，耐心等待；日志: $STATE_DIR/ttsd.log）..."
for i in $(seq 1 120); do
  if [[ -S "$STATE_DIR/ttsd.sock" ]] && grep -q "监听" "$STATE_DIR/ttsd.log" 2>/dev/null; then
    log "守护进程就绪"
    break
  fi
  if grep -qE "Traceback|Error" "$STATE_DIR/ttsd.log" 2>/dev/null; then
    tail -15 "$STATE_DIR/ttsd.log" >&2
    fail "守护进程启动报错，见上方日志（排障指南见 SKILL.md「已知问题」）"
  fi
  sleep 5
done
[[ -S "$STATE_DIR/ttsd.sock" ]] || fail "等待 600s 后守护进程仍未就绪，查看 $STATE_DIR/ttsd.log"

# ── 6. 自测 ─────────────────────────────────────────────────────
if [[ $SKIP_TEST -eq 0 ]]; then
  log "运行 selftest（T1–T5）..."
  .venv-moss/bin/python selftest.py || true
  grep -q '"overall": "pass"' selftest_report.json && log "selftest 全部通过" || \
    echo "[setup] ⚠ selftest 未全过，查看 selftest_report.json（T5 依赖 T3 通路）"
fi

echo
log "✅ 部署完成。朗读测试: $DIR/run.sh \"你好，部署成功\""
log "   其他 App 收音: 麦克风选择 BlackHole 2ch"
exit 0
