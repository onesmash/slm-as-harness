# Claim Evidence Map

| # | Claim(陈述) | claim_type | Evidence refs | Claim level |
| --- | --- | --- | --- | --- |
| C1 | Graph Engineering 是把多 agent/工具/人工审批编排为显式执行图的方法论,节点=职责单一的工作单元,边=带结构化数据的控制流(顺序/条件/扇出/汇聚/循环) | objective | W2, W3 | 高(多方一致) |
| C2 | 该术语 2026 年前后成为热词,且是 engineering 分层栈(prompt→context→harness→loop→graph)的顶层 | objective | W2, W4 | 中 |
| C3 | Anthropic "Building effective agents" 的 5 种模式(prompt chaining/routing/parallelization/orchestrator-workers/evaluator-optimizer)是"用文字描述的图拓扑";并区分确定性 workflow vs 自主 agent loop | objective | W1, W2 | 高 |
| C4 | Anthropic 多智能体研究系统采用 Lead Agent + 并行 subagent + citation agent,在内部研究 eval 上较单 agent +90.2%、token 成本约 15× | objective | W2 | 中(二手转述) |
| C5 | Claude Code "Dynamic Workflows" 是 graph engineering 的落地:确定性 JS 编排脚本,`agent()`=节点,`parallel()`/`pipeline()`=边,脚本确定性支持 checkpoint-resume | objective | W2 | 中(二手转述) |
| C6 | durable-workflow-runtime 通过 `bridge.py start/resume` 协议驱动:`start→yield→host执行→Observation→resume→done`;`response.kind∈{yield,done,error}`、`Observation.status∈{succeeded,failed,blocked,partial}` 两个命名空间不可混用 | objective | S1 | 高(一手) |
| C7 | 运行时把 run state 用 `FileRunStateStore` 持久化到磁盘,`resume` 可从持久化状态恢复(durable),并记录 HistoryEntry 事件日志 | objective | S2 | 高(一手) |
| C8 | 运行时显式建图:workflow 的 `graphbuilder_runtime.py` 导入 `pydantic_graph.graph_builder.Graph/GraphBuilder`,用 `BUILDER.add_edge` 构建执行图;业务节点为 `NodeDefinition(step_id/prompt/intent/expected_artifact/resume_instructions/final/done_when)` | objective | S3 | 高(一手) |
| C9 | 图的边由 `policy.choose_next_node` 依据 `Observation.status` + `verifier_result` 路由(TransitionDecision);业务流程含条件回边(如 `continue_optimization is_true` 回 `diagnose_performance`)与修复/解阻子图(repair_and_resume、request_unblocking_input) | objective | S3, S5 | 高(一手) |
| C10 | 每步有 StepContract:done_when/output_schema/failure_schema/skill_routing/verifier;验证器为 python_callable、run_on_status=["succeeded"],verifier_failed 触发重试并带 retry_context | objective | S4, S2, S1 | 高(一手) |
| C11 | skill_routing 把每个节点路由到专门 skill(performance-nex/brainstorming-nex/research-nex/requesting-code-review/code-kb-workflow/subagent-driven-development…)= 类似"org graph"(谁拥有哪个节点) | objective | S4 | 高(一手) |
| C12 | 运行时核心目标之一是"可恢复的确定性长流程":max_steps 上限、blocked 需人工输入、跨会话 resume —— 这是其区别于通用 graph 编排的侧重点 | objective | S1, S2, S5 | 高(一手) |
| C13 | durable-workflow-runtime 是 graph engineering 思想的一种具体落地:节点=业务阶段、边=policy 路由、提示契约=节点输出契约、验证器=maker/checker 分离 | subjective(分析判断) | 综合 S1-S6 vs W1/W2 | 分析性,非直接可验证 |
| C14 | 差异:graph engineering 方法论强调并行/扇出/汇聚(多 agent 并行、worktree 隔离),而 durable 引擎当前是"单 host 串行、一次一个节点"的 yield/resume 轮转,并行度受限 | objective | S1, S2 vs W2, W3 | 中 |
| C15 | 差异:graph engineering 中数据"沿边流动"(schema 校验的 handoff),而 durable 把状态集中序列化进 `graph_state` 并持久化,由模板上下文注入下一节点 —— 状态经共享持久层而非纯边传递 | objective | S2, S3, S4 | 高(一手) |
| C16 | 差异:graph engineering 是通用方法论,`durable-workflow-runtime` 是带 workflow-creator(自动生成新 workflow)的具体实现产物 | objective | S1, S6 | 高(一手) |
| C17 | 批评视角:graph engineering 术语与旧义 knowledge graph(数据图)冲突;该方法并非全新(LangGraph/AutoGen/ADK 早已有);多数任务不需要图,简单可靠 loop 即可 | objective | W2, W3 | 中(二手) |
| C18 | 选型建议:单 agent 可完成的、需快速迭代的任务用简单 loop;需要并行/多 agent 分工选通用 graph 编排;需要长流程可中断恢复、严格验证、blocked 人工介入、跨会话续跑选 durable-workflow-runtime | subjective(规范性建议) | 综合 W1, W2, S1 | 分析性/规范性 |

**claim_type 说明**(VeriScore 约定):C13/C18 等 `subjective`/`normative` 陈述不进入 unsupported 判定,在正文以分析口吻呈现。
