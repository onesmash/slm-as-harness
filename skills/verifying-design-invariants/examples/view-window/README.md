# 冒烟测试：一对同构模型，正确版 exit 0 / 破坏变体 exit 1

改这个技能之前，先在这里跑一遍。它验证的不是「模型对不对」，而是**这台机器上从模型到判定到图这条路是通的**。

**这个模型不是范本，是最小骨架**：它抽象掉了内容身份（哪几条），只留「视图该显示几条」。但它把规则写成**两个变量之间的关系**（`viewCount = Wanted(count)`），所以规则真的能被违反——这一点是刻意的，见下面「边界」。

## 跑

**用自清 runner**：模型与 `--out` 目录全在临时目录里，技能树保持只读——跑完树哈希不变，
冻结快照不会被写穿；也不再有「第二次跑 `out/` is not empty → exit 2」的坑（每次都是全新目录）。

```sh
bash <技能目录>/examples/view-window/run.sh
# 退出码 0 = 正确版守住（exit 0）+ 破坏变体报红（exit 1）；1 = 任一不符；2 = 未判定（缺 node / statechart）
```

要手动跑 statechart（用于看图），先拷到临时目录、`--out` 指向那里的新目录。
旧文档让人在技能树里直接跑再 `rm -rf out outbug` 清理——那条路留着写穿快照的口子，别再走。

## 预期输出（2026-11-22 21:2x 实测）

正确版：

```
# ViewWindow

TLC reached 5 states and 4 steps. The chart draws 5 states and 4 arrows.

## Rules that hold
ViewInSync, NoDeadlock
```
`green exit=0`

破坏变体：

```
# ViewWindowBug

TLC reached 5 states and 4 steps. The chart draws 5 states and 4 arrows.

## ViewInSync breaks
The shortest path has 4 steps:
0. viewCount=0 pc="idle" count=0
1. AppendLine: viewCount=1 pc="appended" count=1
2. Rebuild: viewCount=1 pc="ready" count=1
3. AppendLine: viewCount=1 pc="appended" count=2
4. Rebuild: viewCount=2 pc="ready" count=2
```
`red exit=1`

## 三个数各自是什么意思（别混）

| 说法 | 来源 | 值 |
|---|---|---|
| `states` | report.md 第一段，TLC 生成的不同状态数 | 5 |
| `steps` | report.md 第一段的原文用词，指图上转移（边）的条数 | 4 |
| 最短违规路径 | report.md 的 "The shortest path has N steps"，N 是**步数**，路径上列 N+1 个状态 | 4 步 / 5 个状态 |

前两个数字**原样引用 report.md**，不要自己换算；第三个只看 `## ViewInSync breaks` 段。

**破坏变体那组「5 states and 4 steps」不等于扫完整个状态空间**：TLC 撞到违规就停，后面的状态不会枚举。所以它和正确版数字碰巧相同，不代表两边跑了一样多的状态——要报覆盖率，跑正确版（无违规）那一次。

## 两条要记住的事

1. **退出码就是门**：规则守住 0，任何规则破 1。可以直接放进 CI，不需要解析文本。
2. **两个版本只差一行逻辑**（`Rebuild` 里 `viewCount'` 从 `Wanted(count)` 改成 `count`）。破坏变体该有的样子：改动最小、理由可预期、报红可复现。

## 边界（重要）

- 模型里没有 `ledger` 序列，**内容身份被抽象掉了**：它证明的是「视图该显示几条」，不是「显示的是最后 60 条中的哪 60 条」。
- 因此这条不变量只能抓住「窗口大小算错/没更新」这一类 bug，抓不住「取了前 N 条而不是后 N 条」。真实性质必须再引入能区分前后位置的变量（例如首行 id）。
- 图上标签是变量赋值原文，因为这里没给 `--view`。给人看要写 view 模块导出 `state()` / `step()`，用读者的话命名状态。
