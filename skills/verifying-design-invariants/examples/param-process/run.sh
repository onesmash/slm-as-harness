#!/bin/bash
# 参数化进程示例的自清 runner：PlusCal 源拷进临时目录，翻译 + 模型检查，产物不落在技能树里。
# 退出码三态：0 = 守住 + 破坏变体按预期报红；1 = 任一不符；2 = 未判定（缺 Java / jar / 翻译器）
# 用法：bash examples/param-process/run.sh   （JAVA / TLA2TOOLS 可覆盖）
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
JAVA_BIN="${JAVA:-java}"
TLA_JAR="${TLA2TOOLS:-$HOME/tools/tla/tla2tools.jar}"

command -v "$JAVA_BIN" >/dev/null 2>&1 || { echo "未判定：找不到 Java（设 JAVA=<路径>）" >&2; exit 2; }
[ -f "$TLA_JAR" ] || { echo "未判定：找不到 tla2tools.jar（设 TLA2TOOLS=<路径>）" >&2; exit 2; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/vdi-param.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM
cp "$HERE/Mutex.tla" "$HERE/MutexBroken.tla" "$HERE/good.cfg" "$HERE/broken.cfg" "$WORK/"
cd "$WORK"

# 第一步：PlusCal → TLA+。翻译器不存在时是「未判定」，不是失败。
for m in Mutex MutexBroken; do
  "$JAVA_BIN" -cp "$TLA_JAR" pcal.trans "$m.tla" > "$m.pcal.log" 2>&1
  if [ $? -ne 0 ]; then
    echo "未判定：$m 的 PlusCal 翻译失败，见 $m.pcal.log" >&2
    sed -n '1,5p' "$m.pcal.log" >&2
    exit 2
  fi
done

"$JAVA_BIN" -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC -workers auto \
  -config good.cfg Mutex.tla > good.out 2>&1
rc_good=$?
"$JAVA_BIN" -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC -workers auto \
  -config broken.cfg MutexBroken.tla > broken.out 2>&1
rc_broken=$?
violated="$(grep -c 'Invariant MutualExclusion is violated' broken.out || true)"

echo "守住版：rc=${rc_good}（预期 0）"
echo "破坏变体（抽掉 await 守卫）：rc=${rc_broken}（预期非 0），违规报告=${violated}（预期 ≥1）"

if [ "$rc_good" = "0" ] && [ "$rc_broken" != "0" ] && [ "$violated" -ge 1 ]; then
  echo "PASS param-process：参数化进程能翻译、能模型检查；抽掉守卫就破"
  exit 0
fi
echo "FAIL param-process：与预期不符，先看上面两个退出码" >&2
exit 1
