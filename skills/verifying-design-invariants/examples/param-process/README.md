# 参数化进程：一个算法，N 个同构实例

大多数真实系统的并发形态是「同一段逻辑跑很多份」——N 个 worker、N 个写者、N 个客户端。PlusCal 用**参数化进程**表达它：算法只写一遍，进程集决定有几个实例。

这个例子是两个进程抢一把锁：守住版互斥，破坏变体只抽掉一行 `await`，TLC 立刻报出互斥被违反。

## 语法：本版翻译器不收括号

```pluscal
process P \in {1,2}      \* 能翻译
process (P \in {1,2})    \* 被拒：Expected "=" or "\in" but found "P"
```

这条踩过两次：第一次以为「翻译器不支持 process 块」，第二次以为「不支持参数化进程」，两次都只是写法不对。**本机 pcal.trans 1.12（2024-07）要求进程不写括号。** 换版本时先跑一遍 `run.sh`，别照抄记忆。

翻译后 `pc` 是**按 `self` 索引的向量**，性质要写成对向量的判断：

```
ProcSet == ({1,2})
Init == /\ cs = 0 /\ owner = 0 /\ pc = [self \in ProcSet |-> "Try"]
```

## 跑

```sh
bash <技能目录>/examples/param-process/run.sh
# 退出码 0 = 守住版 rc=0 + 破坏变体报红（含 "Invariant MutualExclusion is violated"）
#        1 = 任一不符；2 = 未判定（缺 Java / tla2tools.jar / 翻译失败）
```

runner 把 PlusCal 源拷进临时目录再翻译，`states/` 与 `*_TTrace_*` 不落在技能树里（toolchain 第 4 条）。

## 两份模型差在哪

```
Mutex.tla        Try:  await owner = 0;  owner := self;   ← 守卫
MutexBroken.tla  Try:                    owner := self;   ← 抽掉守卫
```

守卫没了，两个进程可以同时进 `Enter`，`cs` 走到 2，`MutualExclusion == cs <= 1` 报红。**这就是 S1 出口判据①「见过它失败」**：不是把性质写下来就算，要看见它被反例打红。

## 什么时候该用它

- 同一段逻辑有多个实例，且实例之间只差一个标识（`self`）
- 想避免手工展开 N 份几乎相同的进程
- 性质是**全局**的（互斥、计数上界、无重复），而不是某个实例的局部性质

反过来，**实例行为不同**时不要硬套参数化：那会把差异藏进 `if self = 1 then ...`，模型读起来比展开更难懂。
