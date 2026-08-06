# Source Matrix — Graph Engineering(概念) vs durable-workflow-runtime

| ID | Source | Kind | Grade | Freshness | Coverage |
| --- | --- | --- | --- | --- | --- |
| S1 | `skills/durable-workflow-runtime/SKILL.md` | 本地一手代码文档 | A | current | durable 的桥协议/职责分层 |
| S2 | `.../workflow-runtime/runtime/engine_graphbuilder.py` | 本地一手源码 | A | current | 运行时引擎:start/resume、FileRunStateStore、verifier、图预览 |
| S3 | `.../workflows/performance_optimization_cycle/graphbuilder_runtime.py` | 本地一手源码 | A | current | pydantic-graph 显式建图、NodeDefinition、边路由 |
| S4 | `.../workflows/performance_optimization_cycle/contract.py` | 本地一手源码 | A | current | StepContract:done_when/output_schema/failure_schema/verifier/skill_routing |
| S5 | `.../workflows/performance_optimization_cycle/references/flowchart.md` | 本地一手文档 | A | current | 业务流程图:节点/条件边/回边/修复子图 |
| S6 | `.../references/index.md` | 本地一手文档 | A | current | skill 布局与读取边界 |
| W1 | Anthropic "Building effective agents" (anthropic.com/engineering) | 一手官方文章 | A | 2024-12 | 5 种 workflow 模式;workflow vs agent 判定 |
| W2 | WebSearch 综合摘要:"graph engineering" 概念(含 Anthropic multi-agent research system、Claude Code Dynamic Workflows、分层模型、LangGraph 先例) | 二手综合 | B | 2025-06 ~ 2026-07 | 概念分层、节点/边词汇、并行、成本 |
| W3 | "The Useful Part of Graph Engineering Is Not the Graph" (pub.towardsai.net) | 社区评论 | C | 2026 | org graph + work graph 双图;批评视角 |
| W4 | "Prompt Engineering vs Loop Engineering vs Graph Engineering" (marktechpost / ai-trends) | 社区评论 | C | 2026-07 | engineering 分层栈;各层变化 |

**来源类别统计**:本地一手源码/文档(A)=6,官方文章(A)=1,二手综合(B)=1,社区(C)=2 → source_class_count = 3(A/B/C)≥2 ✓
