# S4 的最小可用日志校验器

S4 的出口判据是「用规格校验真实日志，能报出模型未覆盖的行为」。本机没装 PObserve，这个脚本给 Node 侧一个能跑的最小替代：**不需要埋点**，只要日志里有「动作名 + 规则要用的字段」。

## 跑

```sh
cd <技能目录>/examples/log-check
PATH=${NODE_BIN:-/usr/local/bin}:$PATH node check-log.mjs ledger.spec.mjs good.log.jsonl          # PASS
PATH=${NODE_BIN:-/usr/local/bin}:$PATH node check-log.mjs ledger.spec.mjs bad.log.jsonl           # FAIL：与规格不符
PATH=${NODE_BIN:-/usr/local/bin}:$PATH node check-log.mjs ledger.spec.mjs empty-trace.log.jsonl   # FAIL：违反规则
PATH=${NODE_BIN:-/usr/local/bin}:$PATH node check-log.mjs ledger.spec.mjs thin.log.jsonl          # UNDECIDED：缺字段
```

## 规格模块的契约（五个导出，两套字段必须分清）

| 导出 | 含义 |
|---|---|
| `initial` | 初始状态对象 |
| `compared` | **规格能算出来**、必须与日志逐字段一致的字段（示例里是 `count` / `viewCount` / `pc`；旧名 `required` 仍兼容） |
| `loggedOnly` | **规格不计算**、只从日志取给规则用的字段（如 `traceId`、外部时间戳、别的进程写的标记），可缺省 |
| `actions` | `{ 动作名: (state, event) => nextState }` |
| `rules` | `{ 规则名: (observed) => boolean }`，`observed` 来自**日志**，不是规格算出来的值 |

两套字段搞混就出事，这是本脚本唯一容易写错的地方：

- 把「规格不计算的字段」放进 `compared` → `compare` 每步都报不符（`expected` 是 `undefined`）
- 把「规格应当算出来的字段」只放进 `loggedOnly` → 规则读它，但**没人比对它**

## 实测输出（2026-11-22 21:4x）

正确日志：

```json
{ "verdict": "PASS", "steps": 4 }
```
`exit=0`

坏日志（第 4 步 `viewCount` 记成 2，规格要求 1）：

```json
{
  "verdict": "FAIL",
  "reason": "第 4 步与规格不符",
  "step": 4,
  "diffs": [{ "step": 4, "field": "viewCount", "expected": 1, "logged": 2 }]
}
```
`exit=1`

`traceId` 为空（`traceId` 在 `loggedOnly`，规格根本不计算它，只能靠规则抓）：

```json
{
  "verdict": "FAIL",
  "reason": "第 1 步违反规则 TraceIdWellFormed",
  "step": 1,
  "rules": ["TraceIdWellFormed"]
}
```
`exit=1`

缺字段（日志里没有 `viewCount` 与 `traceId`）：

```json
{ "verdict": "UNDECIDED", "step": 1, "reason": "缺少字段 viewCount, pc, traceId：日志不足以判定" }
```
`exit=2`

## 三个判定，别混

| verdict | 退出码 | 何时出现 |
|---|---|---|
| `PASS` | 0 | 每步与规格一致，规则全守住 |
| `FAIL` | 1 | ①步骤与规格不符（步号 + 字段 + expected/logged）；②违反规则；③规则求值抛错（单列 `errors`）；④日志含非法 JSON 行（证据本身坏了，不许静默跳过） |
| `UNDECIDED` | 2 | ①缺 `compared` / `loggedOnly` / `action` 里任何一项；②日志是空的。**不等于通过**，也不等于失败 |

`FAIL` 要修代码或修证据，`UNDECIDED` 要补日志——处置不同，混成一个数字就会做错事。

## 设计上的三条硬规矩（照抄别改）

1. **期望值由规格推进，规则判定在日志状态上。** 两者别搞反：拿日志里的状态继续往下推 = 让日志自己给自己作证；拿规格算出来的状态去跑规则 = 规则只是在给自己打分。
2. **规则求值抛错要单独报，不许吞成「违反」或「通过」。** 抛错说明规则自己有问题，跟输入缺字段是两件事（后者走 `UNDECIDED`）。
3. **缺「已声明」的字段直接 `UNDECIDED`，不猜默认值。** 这正是 trace validation 假通过的来源（日志不全时被错误接受）。
   注意与下一条的区别：**没声明**的字段不在此列——读它会拿到 `undefined`，表现为规则违反的假 FAIL，属规格作者错误（脚本不做反射猜测）。

补充一条规格作者须知：**规则只能读 `compared` ∪ `loggedOnly` 里声明过的字段**，读别的会拿到 `undefined`（表现为「规则违反」的假 FAIL，而不是报错）。这是刻意的——不做反射猜测——所以漏声明属规格作者错误。

脚本还会在开跑前做两项契约自检（都按 `FAIL` 退出，避免「假 PASS」）：

```json
{ "verdict": "FAIL", "reason": "规格同时导出了 compared 与 required：请只留一个（required 是旧名）" }
{ "verdict": "FAIL", "reason": "字段同时出现在 compared 与 loggedOnly：viewCount（会被比对又喂给规则，语义不明）" }
```

## 规则检查到底加了多少东西（诚实版）

- 一条规则如果**只用 `compared` 里的字段**，`compare` 会先一步报错，规则检查不提供额外检测力。
- 规则检查的价值在于读 `loggedOnly` 里的字段：**规格推不出来的信息**（上面的 `traceId` 就是最小例子），只能靠日志自己比。
- 所以：**「规则全守住」不等于「日志对得上」**。报告里要写清每条规则读了哪些字段、这些字段属于哪一套。

## 它做不到什么（写进 S4 报告）

- 只检查**日志里出现过的动作序列**，不探索没发生的交错 —— 那是 S1 模型检查的活
- 不验证「日志本身完整」：代码少写一条日志，这里看不出来。日志完整性要另证（对照代码里的写日志点）
- 不做时间/并发重排；乱序日志要先按 `step` 排序再喂
- 想要「从日志自动推断规格」那种能力，得上 PObserve 一类工具（本机未装）

## 接到 S4 的出口判据上

- **能报出模型未覆盖的行为吗？** 能——日志里出现 `actions` 里没有的动作名，会 FAIL 并指名。这时应回 S1 补模型，而不是把动作加进 `actions` 了事。
- **日志够细吗？** `UNDECIDED` 就是这个问题的答案；报告里要写清缺哪个字段。
- **失败在哪一步？** `step` + `field` + expected/logged（或 `rules` / `errors`）就是答案，不用「反例见附件」。
