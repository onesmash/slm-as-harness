#!/bin/bash
# liveness 冒烟的自清 runner：模型拷进临时目录跑，states/ 与 *_TTrace_* 一个都不落在技能树里。
# （toolchain 第 4 条「别在仓库里跑」；2026-11-24 的 test-skill 冻结快照就是被这套例子写穿的。）
#
# 退出码三态：0 = 公平版守住 + 破坏变体按预期报红；1 = 任一不符；2 = 未判定（缺 Java / jar）
# 用法：bash examples/liveness/run.sh   （JAVA / TLA2TOOLS 可覆盖）
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
JAVA_BIN="${JAVA:-java}"
TLA_JAR="${TLA2TOOLS:-$HOME/tools/tla/tla2tools.jar}"

command -v "$JAVA_BIN" >/dev/null 2>&1 || { echo "未判定：找不到 Java（设 JAVA=<路径>）" >&2; exit 2; }
[ -f "$TLA_JAR" ] || { echo "未判定：找不到 tla2tools.jar（设 TLA2TOOLS=<路径>）" >&2; exit 2; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/vdi-liveness.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM
cp "$HERE/Liveness.tla" "$HERE/fair.cfg" "$HERE/unfair.cfg" "$WORK/"
cd "$WORK"

"$JAVA_BIN" -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC -workers auto \
  -config fair.cfg Liveness.tla > fair.out 2>&1
rc_fair=$?
"$JAVA_BIN" -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC -workers auto \
  -config unfair.cfg Liveness.tla > unfair.out 2>&1
rc_unfair=$?
violated="$(grep -c 'AlwaysEventuallyReady was violated' unfair.out || true)"

echo "公平版：rc=${rc_fair}（预期 0）"
echo "破坏变体（抽掉 WF_vars）：rc=${rc_unfair}（预期 13），违规报告=${violated}（预期 ≥1）"

if [ "$rc_fair" = "0" ] && [ "$rc_unfair" = "13" ] && [ "$violated" -ge 1 ]; then
  echo "PASS liveness：活性依赖公平性——抽掉 WF 就破，公平版守住"
  exit 0
fi
echo "FAIL liveness：与预期不符，先看上面两个退出码" >&2
exit 1
