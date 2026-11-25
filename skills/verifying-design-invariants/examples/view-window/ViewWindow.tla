---- MODULE ViewWindow ----
\* 抽象：帐本是唯一真相，房间视图 = 帐本最后 MaxLen 条（这里取 MaxLen = 1）。
\* 变量的语义：count = 帐本里的条数；viewCount = 视图里显示的条数；pc = 进程位置。
\* 内容身份（哪几条）被抽象掉了，只留「视图该显示几条」这一维——
\* 但规则写成两个变量之间的关系，所以它真的能被违反。
EXTENDS Naturals

VARIABLES count, viewCount, pc
vars == <<count, viewCount, pc>>

\* 帐本有 n 条时，MaxLen = 1 的视图应显示几条
Wanted(n) == IF n = 0 THEN 0 ELSE 1

Init ==
    /\ count = 0
    /\ viewCount = 0
    /\ pc = "idle"

\* 追加一条：写完帐本立刻把视图刷新到最新
AppendLine ==
    /\ pc \in {"idle", "ready"}
    /\ count' = count + 1
    /\ viewCount' = Wanted(count')
    /\ pc' = "appended"

\* 进程重启：从帐本重建视图（这一步做错，就是我们要抓的那类 bug）
Rebuild ==
    /\ pc = "appended"
    /\ count' = count
    /\ viewCount' = Wanted(count)
    /\ pc' = "ready"

Next == AppendLine \/ Rebuild

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

\* 界：只保留最近 2 次追加，状态空间有限
StateConstraint == count <= 2

\* 规则：视图显示的条数必须等于「帐本当前应有的窗口大小」。
ViewInSync == viewCount = Wanted(count)

====
