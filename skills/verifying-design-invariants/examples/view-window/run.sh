#!/bin/bash
# view-window 冒烟的自清 runner：模型拷进临时目录，statechart 的 out/ 也落在那里。
# 技能树保持只读——跑完树哈希不变，test-skill 的冻结快照不会被写穿。
#
# 退出码三态：0 = 正确版 exit 0 + 破坏变体 exit 1；1 = 任一不符；2 = 未判定（缺 node / statechart）
# 用法：bash examples/view-window/run.sh   （NODE_BIN / SC / JAVA / TLA2TOOLS 可覆盖）
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PATH="${NODE_BIN:-/usr/local/bin}:$PATH"
SC_BIN="${SC:-$HOME/.agents/skills/statechart/scripts/statechart}"

command -v node >/dev/null 2>&1 || { echo "未判定：找不到 node（设 NODE_BIN=<目录>）" >&2; exit 2; }
[ -x "$SC_BIN" ] || { echo "未判定：找不到 statechart（设 SC=<路径>）" >&2; exit 2; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/vdi-viewwindow.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM
cp "$HERE"/ViewWindow*.tla "$HERE"/ViewWindow*.cfg "$WORK/"
cd "$WORK"

PATH="${NODE_BIN:-/usr/local/bin}:$PATH" JAVA="${JAVA:-/usr/bin/java}" \
TLA2TOOLS="${TLA2TOOLS:-$HOME/tools/tla/tla2tools.jar}" \
"$SC_BIN" ViewWindow.tla --config ViewWindow.cfg --out out/ > green.out 2>&1
rc_green=$?
PATH="${NODE_BIN:-/usr/local/bin}:$PATH" JAVA="${JAVA:-/usr/bin/java}" \
TLA2TOOLS="${TLA2TOOLS:-$HOME/tools/tla/tla2tools.jar}" \
"$SC_BIN" ViewWindowBug.tla --config ViewWindowBug.cfg --out outbug/ > red.out 2>&1
rc_red=$?

echo "正确版：rc=${rc_green}（预期 0）"
echo "破坏变体（窗口取全量条数）：rc=${rc_red}（预期 1）"

if [ "$rc_green" = "0" ] && [ "$rc_red" = "1" ]; then
  echo "PASS view-window：正确版守住、破坏变体报红"
  exit 0
fi
echo "FAIL view-window：与预期不符（若报 out/ is not empty 不该发生——runner 每次用全新临时目录）" >&2
exit 1
