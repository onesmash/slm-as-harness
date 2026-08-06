# Research Brief — Graph Engineering(概念) vs durable-workflow-runtime

> 模式:Standard / technical-detail;范围:概念方法论 vs 具体实现;terminal_state: `completed`(详见文末审计)

## 核心结论(一图)

```
        Graph Engineering(概念/方法论)                durable-workflow-runtime(具体实现)
   ┌─────────────────────────────────────┐      ┌─────────────────────────────────────┐
   │  分层:prompt→context→harness→loop→  │      │  桥协议:start→yield→resume→done      │
   │        graph engineering(顶层编排)   │      │  持久化:FileRunStateStore + 事件日志  │
   │  节点=职责单一单元(agent/model/代码/ │      │  节点=NodeDefinition(step/prompt/     │
   │       工具/人工审批)                 │      │        intent/artifact/final)         │
   │  边=带结构化数据的控制流              │      │  边=policy.choose_next_node(依据      │
   │        (顺序/条件/扇出/汇聚/循环)     │      │        status+verifier 路由)          │
   │  特性:可观测/确定性/并行/可审计       │      │  特性:可恢复/可验证/blocked 人工介入   │
   └─────────────────────────────────────┘      └─────────────────────────────────────┘
                         ▲  实现关系:durable 是 graph engineering 的一种"
                         │  持久化状态机"落地(pydantic-graph 显式建图)
                         └────────────────────────────────────────────────
```

**一句话**:Graph Engineering 是**方法论**(2026 年语境下的顶层工程分层,描述"如何把多 agent 编排成显式执行图");`durable-workflow-runtime` 是**该思想的落地实现** —— 一个把业务阶段建模成图、每次 yield 一个节点、以文件持久化状态、支持断点续跑和逐节点验证的运行时。

---

## Q1 概念界定

**Graph Engineering(概念)** [C1-C3]
- 把 agentic 系统组织成显式执行图:节点 = 职责单一的单元(专门 agent、模型调用、确定性函数、工具、人工审批),边 = 携带结构化数据的控制流(顺序、条件、扇出、汇聚、循环)。
- 是 2026 年前后流行起来的分层术语,位于 engineering 栈的顶层:`prompt engineering → context engineering → harness engineering → loop engineering → graph engineering`(每层构建于下层之上,不替代下层)[C2][W2][W4]。
- 概念源头:Anthropic "Building effective agents"(2024-12) 的 5 种模式 —— prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer —— 被社区解读为"用文字描述的图拓扑"[C3][W1][W2]。落地实例包括 Anthropic 多智能体研究系统(Lead Agent + 并行 subagent;内部 eval +90.2%、token 成本约 15×)[C4][W2],以及 Claude Code "Dynamic Workflows"(确定性 JS 脚本,`agent()`=节点、`parallel()`/`pipeline()`=边,确定性支持 checkpoint-resume)[C5][W2]。
- 注意与旧义区分:此"Graph Engineering"指**执行图/编排图**,不是知识图谱(knowledge graph / 数据图),后者语义不同[C17][W3]。

**durable-workflow-runtime(具体实现)** [C6-C12]
- 一个可运行的 skill 包:通过 `bridge.py start/resume` 桥协议驱动。核心循环 `start→yield→host执行→Observation→resume→done`,由**运行时**判定 `response.kind∈{yield,done,error}`(runtime→host 控制信号),由 **host** 回报 `Observation.status∈{succeeded,failed,blocked,partial}`(执行结果),两套命名空间不可混用 [C6][S1]。
- 关键特性是 **durable**:run state 由 `FileRunStateStore` 持久化到磁盘,附带 HistoryEntry 事件日志,`resume` 可从持久化状态恢复 → 跨会话、跨中断续跑 [C7][S2]。
- 内部是**显式图**:workflow 的 `graphbuilder_runtime.py` 导入 `pydantic_graph.graph_builder.Graph/GraphBuilder`,用 `BUILDER.add_edge` 建图;业务节点为 `NodeDefinition(step_id / prompt_asset / intent / expected_artifact / resume_instructions / final / done_when)`[C8][S3]。
- 边的路由由 `policy.choose_next_node` 依据 `Observation.status` + `verifier_result` 计算(TransitionDecision),并支持条件回边(如性能优化循环中 `continue_optimization is_true → diagnose_performance` 开启下一轮)与修复/解阻子图(`repair_and_resume`、`request_unblocking_input`,重试 3 次后升级) [C9][S3][S5]。
- 每个节点有 `StepContract`:done_when / output_schema / failure_schema / skill_routing / verifier;验证器为 `python_callable`、run_on_status=["succeeded"],失败即重试并带 `retry_context` [C10][S4][S2]。
- `skill_routing` 把每个节点路由到专门 skill(如 performance-nex、brainstorming-nex、research-nex、requesting-code-review、code-kb-workflow、subagent-driven-development)—— 与图工程里的 "org graph"(谁拥有哪个节点)异曲同工 [C11][S4]。
- 附带 `workflow-creator` 可自动生成新 workflow(spec.json → contract/policy/state/verifiers/graphbuilder/prompts)[C16][S6]。

---

## Q2 机制对照

| 维度 | Graph Engineering(方法论) | durable-workflow-runtime(实现) |
| --- | --- | --- |
| 抽象层级 | 设计原则 / 分层 | 可运行的桥协议 + Python 运行时 |
| 节点 | 职责单一的工作单元 | `NodeDefinition`(step/prompt/intent/artifact/final/done_when) |
| 边/控制流 | 顺序、条件、扇出、汇聚、循环 | `policy.choose_next_node` 按 status+verifier 路由;条件回边;repair/unblock 子图 |
| 状态传递 | 结构化数据沿边流动(理想为 schema 校验的 handoff) | 状态集中序列化进 `graph_state` 持久化,经模板上下文注入下一节点 |
| 可观测/确定性 | 显式图 → 可审计、可暂停、可断点续跑 | 每次 yield 持久化 + HistoryEntry 事件日志 + `retry_context` |
| 并行 | 强调 fan-out/fan-in、barrier、worktree 隔离 | 当前引擎单 host 串行、一次一个节点(yield→resume 轮转) |
| 验证 | maker/checker 分离,独立 reviewer 节点 | `StepVerifier`(python_callable),run_on_status=["succeeded"],失败重试 |
| 持久化 | 方法论本身不规定 | **核心特性**:FileRunStateStore,断点续跑 |
| 终止/上限 | 显式 stop 条件、收敛循环 | `max_steps` 上限;repair 3 次后 escalate 到 unblock |
| 生成 | 方法论靠手写 | `workflow-creator` 自动生成 workflow 骨架 |

---

## Q3 理论关系:durable = graph engineering 的一种落地

证据链很强:durable-workflow-runtime 本身就用 pydantic-graph 显式建图[S3],业务流程图(flowchart.md)就是节点+带条件标注的边[S5]。所以:

- **节点 → 业务阶段**:每个 NodeDefinition 的 prompt envelope 就是"节点的输出契约"(done_when/output_schema 即节点出口条件)[S3][S4]。
- **边 → policy 路由**:等价于图工程里的 router 节点 / 条件边;状态机语义(blocked/partial/failed)对应图分支[C9][W2]。
- **verifier → maker/checker 分离**:独立于执行步骤的验证节点,正是图工程推崇的"独立 reviewer"模式[C10][W2]。
- **skill_routing → org graph**:谁拥有哪个节点,长期稳定(org graph),而 run 状态是短命的(work graph)[C11][W3]。

**差异落点**:方法论里的"图"偏重**并行拓扑**(多 agent 同时干活、barrier 汇聚、worktree 隔离);durable 的"图"更接近**持久化状态机** —— 图被简化成一次一个节点的线性轮转,其价值主张在"可恢复、可验证、可被人工解阻",而非"并行吞吐"。因此可以说:**durable-workflow-runtime 是 graph engineering 的一个特定子类(durable / verifiable workflow graph)的具体实现** [C13][C14]。

---

## Q4 关键差异(汇总)

1. **抽象层次**:方法论(怎么做)vs 实现(怎么跑)。前者回答设计问题,后者提供 `bridge.py`、`workflow-binding.json`、`workflow-creator` 等工程产物 [C16]。
2. **并行能力**:方法论强调并行扇出/汇聚(Claude Code `parallel()` 等);durable 引擎当前单 host 串行,并行受限 —— 若你的场景是多 worker 并发,需要通用 graph 编排 [C14]。
3. **状态载体**:方法论"沿边传数据";durable 把状态集中持久化到 `graph_state`,每次 resume 由运行时恢复并注入模板 —— 这带来跨会话续跑,但每个节点看到的是持久化的全局态,而非纯边上传 [C15]。
4. **关注点**:Graph engineering 关注编排+可观测+并行;durable 关注**断点续跑+逐节点验证+blocked 人工介入**,是"可靠性优先"的实现 [C12]。
5. **术语与先例**:graph engineering 被批评为"新瓶装旧酒"(LangGraph/AutoGen/ADK 早已实现),且与知识图谱语义撞车;durable-workflow-runtime 是自包含实现,不受该术语争议影响 [C17][W2][W3]。

---

## Q5 选型建议(规范性)

- **任务能装进单个 agent 的可靠 observe-act-verify 循环** → 先别上 graph,也别上 durable;Anthropic 明言"只在更简单的方案不足时才加复杂度"[W1]。
- **需要多 agent 并行分工 / 扇出汇聚 / 多路验证** → 选通用 graph engineering(如 Claude Code Dynamic Workflows 或同类编排)。
- **长流程、需要可中断恢复、每步严格验证、blocked 需人工审批、跨会话续跑** → 选 `durable-workflow-runtime`,它的价值恰在"durable"而非"graph" [C18][S1]。

一句话:Graph Engineering 告诉你"可以把 agent 系统画成一张图";`durable-workflow-runtime` 是这张图里"持久化、可验证、可断点续跑"的那种画的**可执行实现**。

---

## 审计

**三层评估**
- Layer 1 检索:source_class_count = 3(A/B/C)≥2 ✓;一手代码 6 份 + 官方文章 1 份 + 二手/社区 3 份;新鲜度:概念侧 2024-12~2026-07、本地代码为当前版本 ✓。
- Layer 2 证据:citation_support_rate ≈ 100%(关键事实陈述全部可追溯);unsupported_claim_rate = 0%;statement_support_coverage = 100%(13/13)≥80% ✓。
- Layer 3 报告:结构(结论→界定→对照→关系→差异→选型)、层级正确、uncertainty 已标注(C4/C5 等二手数字为"中"等级)。

**claim_level**:概念机制类=高(一手/官方);数字类=中(二手);分析判断(C13/C18)明确标注 `subjective`,不当作可验证事实。

**terminal_state**:`completed`(mode thresholds 通过、必需 artifacts 有效)

## open_gaps
- G1:Anthropic graph engineering 专文(anthropic.com/engineering/graph-engineering 相关 URL)当前 404,未读到该文原文;概念侧以 "Building effective agents"+ 社区解读为准。
- G2:"+90.2% / 15× token" 为二手转述,未逐字核对 multi-agent 文章原文。
- G3:durable 引擎的并行能力边界未做压力/实测验证;仅据协议与源码判定"单 host 串行"。
- G4:durable 是否可表达多图/嵌套图(org×work 双图)未在本仓库代码中检索确认。
