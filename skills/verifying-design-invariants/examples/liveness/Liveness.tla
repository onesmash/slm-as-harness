---- MODULE Liveness ----
\* 活性性质的破坏变体：不是改代码逻辑，而是把公平性抽掉。
\* Spec      = 带 WF_vars(Next)  -> 进程不会永远停在原地，规则该守住
\* SpecNoFairness = 不带 WF       -> TLC 允许无限 stutter，同一条规则被违反
EXTENDS Naturals

VARIABLES pc
vars == <<pc>>

Init == pc = "idle"

AppendLine ==
    /\ pc \in {"idle", "ready"}
    /\ pc' = "appended"

Rebuild ==
    /\ pc = "appended"
    /\ pc' = "ready"

Next == AppendLine \/ Rebuild

\* 公平版：一直能做下一步，就一直会做
Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

\* 破坏变体：只删掉 WF_vars(Next)
SpecNoFairness == Init /\ [][Next]_vars

\* 活性规则：ready 会被反复到达（不是「最终到达一次」）
AlwaysEventuallyReady == []<>(pc = "ready")

====
