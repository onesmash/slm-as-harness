# 活性性质的破坏变体：抽掉公平性

安全性质的破坏变体是「改一行逻辑」；**活性性质的破坏变体是「抽掉公平性」**。这个例子把两者放在同一份模型里，只差一个 `WF_vars(Next)`。

## 跑

**用自清 runner**：模型拷进临时目录跑，`states/` 与 `*_TTrace_*` 不落在技能树里
（toolchain 第 4 条；曾经照旧文档在树里跑，TLC 写穿了一次冻结快照）。

```sh
bash <技能目录>/examples/liveness/run.sh
# 退出码 0 = 公平版守住（裸 TLC rc=0）+ 破坏变体报红（裸 TLC rc=13）
#        1 = 任一不符；2 = 未判定（缺 Java / tla2tools.jar）
```

要在裸 TLC 下手动跑（用于看完整输出），**先拷到临时目录**：

```sh
W="$(mktemp -d)"; cp <技能目录>/examples/liveness/{Liveness.tla,fair.cfg,unfair.cfg} "$W/"; cd "$W"
"${JAVA:-/usr/bin/java}" -XX:+UseParallelGC -cp "${TLA2TOOLS:-$HOME/tools/tla/tla2tools.jar}" \
  tlc2.TLC -workers auto -config fair.cfg Liveness.tla      # 预期 rc=0
"${JAVA:-/usr/bin/java}" -XX:+UseParallelGC -cp "${TLA2TOOLS:-$HOME/tools/tla/tla2tools.jar}" \
  tlc2.TLC -workers auto -config unfair.cfg Liveness.tla    # 预期 rc=13
rm -rf "$W"
```

## 预期输出（2026-11-22 21:27 实测）

公平版：`4 states generated, 3 distinct states found`，无错误。

破坏变体：

```
Error: Temporal property AlwaysEventuallyReady was violated.
Error: The following behavior constitutes a counter-example:
```

裸 TLC 的退出码：**13**（实测）。不变量违反是 12，通过是 0；`statechart` 那条命令会把违规归一化成 1。CI 里按「非 0 即不通过」判，别写 `== 1`。

## 要点

- **活性性质写进 `.cfg` 的 `PROPERTY`（不是 `INVARIANT`）**，TLC 用 temporal 检查器跑，不是状态枚举。
- **破坏变体 = 破坏公平性**：`Spec == Init /\ [][Next]_vars /\ WF_vars(Next)` 去掉 `WF_vars(Next)`，TLC 就能找到「永远 stutter」的反例。这不是把代码改坏，而是把「系统一定会继续走」这个假设拿掉——它正好证明这条活性规则**依赖**那个假设。
- **不许为了通过而删公平性**：如果模型带 `WF_vars` 时活性成立、不带时不成立，正确结论是「这条活性依赖公平性假设」，写进范围声明；错的做法是悄悄删掉 `WF` 再宣布通过。
- `[]<>(pc = "ready")` 是「无限次到达」，`<>(pc = "ready")` 是「最终到达一次」。两者不是一件事，写性质时说清是哪一个。

## 什么时候用不上

- 性质本身不含时间维度（纯安全性质）→ 用不变量 + 逻辑破坏变体，别硬套这里
- 模型里没有循环（有限 DAG）→ 活性通常退化成「最终到达某个终态」，仍然要有自己的破坏变体
