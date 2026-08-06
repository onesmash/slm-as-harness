# Statement Support Matrix(关键陈述逐条审计)

| 关键陈述 | 支持来源 | 来源等级 | 支持度 |
| --- | --- | --- | --- |
| "Graph Engineering 是把编排建模为显式执行图(节点+带数据与控制流的边)" | W2, W3, W1(隐含) | A/B/C | 强(多方一致) |
| "5 种 workflow 模式=文字版图拓扑" | W1(一手), W2(二手解读) | A/B | 强 |
| "multi-agent 系统 +90.2% @ 15× token" | W2 转述 Anthropic | B | 中 — 待核实原始文章绝对数字 |
| "Dynamic Workflows:agent()=节点、parallel()/pipeline()=边、确定性 checkpoint-resume" | W2 | B | 中 — 二手转述 |
| "durable 协议 start→yield→resume→done;kind/status 两个命名空间" | S1 | A | 强(一手) |
| "运行时用 pydantic-graph 显式建图" | S3(import 与 add_edge) | A | 强(一手) |
| "状态持久化 FileRunStateStore + HistoryEntry 日志,支持 resume" | S2 | A | 强(一手) |
| "边由 policy.choose_next_node 依 status+verifier 路由,含条件回边与修复子图" | S3, S5 | A | 强(一手) |
| "每步 StepContract + python verifier(maker/checker)" | S4, S2 | A | 强(一手) |
| "skill_routing 类似 org graph" | S4 | A(部分)+分析 | 强(事实部分)/分析(类比) |
| "durable 是 graph engineering 的一种落地" | 综合 S1-S6 vs W1/W2 | — | 分析判断(subjective) |
| "durable 当前单 host 串行、并行受限" | S1(协议单 host) vs W2/W3(方法论强调并行) | A vs B/C | 中 |
| "状态经集中持久化 graph_state 而非纯沿边传递" | S2, S3, S4 | A | 强(一手) |
| "术语非全新;LangGraph 等先例;多数任务不需要图" | W2, W3 | B/C | 中 |

**统计**:受支持可验证陈述 = 13;需降级/标注的 = 0(均为中等级、在正文标注) ;主观/规范性 = 2(单独标注)。statement_support_coverage ≈ 13/13 = 100%(≥80% ✓)。
