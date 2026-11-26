#!/bin/bash
# 日志校验示例的自清 runner：四份日志各跑一遍，断言各自的退出码。
# 退出码三态：0 = 四态全符预期；1 = 任一不符；2 = 未判定（缺 node）
# 用法：bash examples/log-check/run.sh   （NODE 可覆盖）
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
NODE_BIN="${NODE:-node}"
command -v "$NODE_BIN" >/dev/null 2>&1 || { echo "未判定：找不到 node（设 NODE=<路径>）" >&2; exit 2; }

cd "$HERE"
fail=0
# 名称 → 预期退出码。good 是唯一该通过的；thin 缺字段属「未判定」而不是失败。
for pair in "good 0" "bad 1" "empty-trace 1" "thin 2"; do
  set -- $pair
  name="$1"; want="$2"
  "$NODE_BIN" check-log.mjs ledger.spec.mjs "$name.log.jsonl" > "$name.out" 2>&1
  got=$?
  if [ "$got" = "$want" ]; then
    echo "  ok   $name: rc=${got}（预期 ${want}）"
  else
    echo "  FAIL $name: rc=${got}（预期 ${want}）" >&2
    sed -n '1,3p' "$name.out" >&2
    fail=1
  fi
  rm -f "$name.out"
done

if [ "$fail" = "0" ]; then
  echo "PASS log-check：四份日志各按预期判定（good 通过 / bad 与 empty-trace 失败 / thin 未判定）"
  exit 0
fi
echo "FAIL log-check：退出码与预期不符" >&2
exit 1
