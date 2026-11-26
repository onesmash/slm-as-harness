---- MODULE Mutex ----
\* 参数化进程的最小示例：两个同构进程共享一把锁。
\* 注意语法：本版 pcal.trans 要写 `process P \in {1,2}`，**加括号 `process (P \in {1,2})` 会被拒**。
\* 破坏变体见 MutexBroken.tla：只抽掉 `await owner = 0` 这一行。
EXTENDS Naturals, TLC
(* --algorithm Mutex
variables owner = 0, cs = 0;

process P \in {1,2}
begin
  Try:
    await owner = 0;
    owner := self;
  Enter:
    cs := cs + 1;
  Leave:
    cs := cs - 1;
    owner := 0;
end process;
end algorithm; *)

\* 互斥：任何时刻至多一个进程在临界区。
MutualExclusion == cs <= 1
====
