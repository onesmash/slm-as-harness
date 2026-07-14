from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_graph.graph_builder import Graph, GraphBuilder

from runtime.models import HistoryEntry, YieldResponse
from workflows.common.policies import TransitionDecision
from workflows.common.prompting import build_prompt_envelope, resolve_prompt_asset

from . import contract as workflow_contract
from . import policy, state as workflow_state

WORKFLOW_VERSION = "v1"
PROMPTS_DIR = Path(__file__).with_name("prompts")


@dataclass(frozen=True)
class NodeDefinition:
    step_id: str
    prompt_asset_path: Path
    intent: str
    expected_artifact: str
    resume_instructions: str
    final: bool = False
    done_when: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GraphBuilderPreviewInputs:
    current_step_id: str
    observation: dict
    verifier_result: dict | None = None


@dataclass(frozen=True)
class GraphBuilderStartInputs:
    run_id: str
    workflow_id: str
    workflow_version: str


@dataclass(frozen=True)
class GraphBuilderPreviewResult:
    step_id: str
    branch_kind: str
    reason: str
    trace_payload: dict
    history_entry: HistoryEntry
    state_payload: dict


@dataclass(frozen=True)
class GraphBuilderTransition:
    current_step_id: str
    decision: TransitionDecision
    state_payload: dict

    def to_trace_payload(self) -> dict:
        return self.decision.to_trace_payload()


NODE_DEFINITIONS = {
    "diagnose_performance": NodeDefinition(
        step_id="diagnose_performance",
        prompt_asset_path=PROMPTS_DIR / "diagnose_performance.md",
        intent="establish_performance_baseline_and_bottleneck",
        expected_artifact="performance baseline, bottleneck summary, and diagnostic report",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "brainstorm_optimization": NodeDefinition(
        step_id="brainstorm_optimization",
        prompt_asset_path=PROMPTS_DIR / "brainstorm_optimization.md",
        intent="form_optimization_hypotheses",
        expected_artifact="scored optimization-hypothesis shortlist and ideation artifact",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "research_optimization": NodeDefinition(
        step_id="research_optimization",
        prompt_asset_path=PROMPTS_DIR / "research_optimization.md",
        intent="gather_optimization_evidence",
        expected_artifact="research brief and evidence map for the selected hypothesis",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "plan_optimization": NodeDefinition(
        step_id="plan_optimization",
        prompt_asset_path=PROMPTS_DIR / "plan_optimization.md",
        intent="write_optimization_implementation_plan",
        expected_artifact="test-first implementation plan for the selected optimization",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "implement_optimization": NodeDefinition(
        step_id="implement_optimization",
        prompt_asset_path=PROMPTS_DIR / "implement_optimization.md",
        intent="implement_and_verify_optimization",
        expected_artifact="implemented candidate with submission-test evidence",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "review_optimization": NodeDefinition(
        step_id="review_optimization",
        prompt_asset_path=PROMPTS_DIR / "review_optimization.md",
        intent="review_optimization_change",
        expected_artifact="review findings and acceptance decision for the optimized kernel",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "update_optimization_knowledge_base": NodeDefinition(
        step_id="update_optimization_knowledge_base",
        prompt_asset_path=PROMPTS_DIR / "update_optimization_knowledge_base.md",
        intent="update_optimization_knowledge_base",
        expected_artifact="updated durable knowledge-base record and next-cycle decision",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "capture_blocked_cycle_knowledge": NodeDefinition(
        step_id="capture_blocked_cycle_knowledge",
        prompt_asset_path=PROMPTS_DIR / "capture_blocked_cycle_knowledge.md",
        intent="capture_blocked_cycle_knowledge",
        expected_artifact="durable knowledge-base record of the blocked stage and its next-cycle learning",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "request_unblocking_input": NodeDefinition(
        step_id="request_unblocking_input",
        prompt_asset_path=PROMPTS_DIR / "request_unblocking_input.md",
        intent="request_unblocking_input",
        expected_artifact='user action needed to unblock the workflow',
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "repair_and_resume": NodeDefinition(
        step_id="repair_and_resume",
        prompt_asset_path=PROMPTS_DIR / "repair_and_resume.md",
        intent="repair_and_resume",
        expected_artifact='repair actions needed before returning to the original stage',
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "finalize_optimization_cycle": NodeDefinition(
        step_id="finalize_optimization_cycle",
        prompt_asset_path=PROMPTS_DIR / "finalize_optimization_cycle.md",
        intent="finalize_summary",
        expected_artifact="final user-facing summary",
        resume_instructions="No further resume.",
        final=True,
        done_when=("Output the final workflow summary",),
    ),
}


BUILDER = GraphBuilder(
    name="performance_optimization_cycle_graphbuilder_runtime",
    state_type=workflow_state.PerformanceOptimizationCycleWorkflowState,
    input_type=GraphBuilderPreviewInputs,
    output_type=GraphBuilderPreviewResult,
    auto_instrument=False,
)


@BUILDER.step(node_id="evaluate_transition")
async def evaluate_transition(ctx) -> GraphBuilderTransition:
    workflow_state.record_observation(
        ctx.state,
        current_step_id=ctx.inputs.current_step_id,
        observation=ctx.inputs.observation,
        verifier_result=ctx.inputs.verifier_result,
    )
    decision = policy.choose_next_node(
        current_step_id=ctx.inputs.current_step_id,
        state=workflow_state.serialize_state(ctx.state),
        observation=ctx.inputs.observation,
        verifier_result=ctx.inputs.verifier_result,
    )
    workflow_state.apply_transition(
        ctx.state,
        current_step_id=ctx.inputs.current_step_id,
        next_step_id=decision.next_node,
    )
    return GraphBuilderTransition(
        current_step_id=ctx.inputs.current_step_id,
        decision=decision,
        state_payload=workflow_state.serialize_state(ctx.state),
    )


@BUILDER.step(node_id="emit_preview_result")
async def emit_preview_result(ctx) -> GraphBuilderPreviewResult:
    trace_payload = ctx.inputs.to_trace_payload()
    return GraphBuilderPreviewResult(
        step_id=ctx.inputs.decision.next_node,
        branch_kind=ctx.inputs.decision.branch_kind,
        reason=ctx.inputs.decision.reason,
        trace_payload=trace_payload,
        history_entry=HistoryEntry.branch_selected(
            node=ctx.inputs.current_step_id,
            step_id=ctx.inputs.current_step_id,
            payload=trace_payload,
        ),
        state_payload=ctx.inputs.state_payload,
    )


BUILDER.add_edge(BUILDER.start_node, evaluate_transition)
BUILDER.add_edge(evaluate_transition, emit_preview_result)
BUILDER.add_edge(emit_preview_result, BUILDER.end_node)


WORKFLOW_GRAPH = BUILDER.build()


START_BUILDER = GraphBuilder(
    name="performance_optimization_cycle_graphbuilder_runtime_start",
    state_type=workflow_state.PerformanceOptimizationCycleWorkflowState,
    input_type=GraphBuilderStartInputs,
    output_type=YieldResponse,
    auto_instrument=False,
)


@START_BUILDER.step(node_id="emit_diagnose_performance")
async def emit_diagnose_performance(ctx) -> YieldResponse:
    node_definition = get_node_definition("diagnose_performance")
    contract = workflow_contract.get_step_contract("diagnose_performance")
    prompt_envelope = build_prompt_envelope(
        run_id=ctx.inputs.run_id,
        step_id=node_definition.step_id,
        prompt_asset_path=node_definition.prompt_asset_path,
        intent=node_definition.intent,
        expected_artifact=node_definition.expected_artifact,
        done_when=contract.done_when,
        output_schema=contract.output_schema,
        failure_schema=contract.failure_schema,
        resume_instructions=node_definition.resume_instructions,
        skill_routing=contract.skill_routing,
        metadata={
            "workflow_id": ctx.inputs.workflow_id,
            "workflow_version": ctx.inputs.workflow_version,
        },
        template_context=_template_context_from_state(ctx.state),
    )
    return YieldResponse(
        run_id=ctx.inputs.run_id,
        step_id=node_definition.step_id,
        prompt_envelope=prompt_envelope,
    )


START_BUILDER.add_edge(START_BUILDER.start_node, emit_diagnose_performance)
START_BUILDER.add_edge(emit_diagnose_performance, START_BUILDER.end_node)


START_GRAPH = START_BUILDER.build()


def build_graph() -> Graph:
    return WORKFLOW_GRAPH


def build_start_graph() -> Graph:
    return START_GRAPH


def get_node_definition(node_key: str) -> NodeDefinition:
    try:
        return NODE_DEFINITIONS[node_key]
    except KeyError as exc:  # pragma: no cover - generated guard
        raise LookupError(f"unknown node definition: {node_key}") from exc


def load_prompt_body(node_key: str, template_context: dict | None = None) -> str:
    return resolve_prompt_asset(
        get_node_definition(node_key).prompt_asset_path,
        template_context=template_context,
    )


def build_template_context(*, step_id: str, run_state) -> dict:
    state = workflow_state.deserialize_state(
        run_state.graph_state if isinstance(run_state.graph_state, dict) else {}
    )
    repair_context = state.repair_context if isinstance(state.repair_context, dict) else {}
    repair_payload = repair_context.get("repair_payload")
    if not isinstance(repair_payload, dict):
        repair_payload = {}
    context = _template_context_from_state(state)
    context.update(
        {
            "current_step_id": step_id,
            "return_stage_id": state.return_stage_id or "",
            "source_stage_id": str(repair_context.get("source_stage_id") or ""),
            "repair_category": str(repair_payload.get("category") or ""),
            "repair_summary": str(repair_payload.get("summary") or ""),
            "repair_requirements": _format_prompt_list(repair_payload.get("requirements")),
            "repair_evidence": _format_prompt_list(repair_payload.get("evidence")),
        }
    )
    return context


def _template_context_from_state(state: workflow_state.PerformanceOptimizationCycleWorkflowState) -> dict:
    task_input_values = state.task_input if isinstance(state.task_input, dict) else {}
    context_values = state.context if isinstance(state.context, dict) else {}
    constraint_values = state.constraints if isinstance(state.constraints, dict) else {}
    context = {
        "workflow_goal": state.workflow_goal or "",
        "task_input_json": json.dumps(state.task_input, ensure_ascii=False, indent=2),
        "context_json": json.dumps(state.context, ensure_ascii=False, indent=2),
        "constraints_json": json.dumps(state.constraints, ensure_ascii=False, indent=2),
    }
    context.update(
        {
        "artifacts_by_stage_json": json.dumps(state.artifacts_by_stage, ensure_ascii=False, indent=2),
        "baseline_metrics": _format_prompt_value(state.baseline_metrics),
        "bottleneck_summary": _format_prompt_value(state.bottleneck_summary),
        "performance_report_path": _format_prompt_value(state.performance_report_path),
        "optimization_hypotheses": _format_prompt_value(state.optimization_hypotheses),
        "success_criteria": _format_prompt_value(state.success_criteria),
        "brainstorm_artifact_path": _format_prompt_value(state.brainstorm_artifact_path),
        "research_brief_path": _format_prompt_value(state.research_brief_path),
        "evidence_summary": _format_prompt_value(state.evidence_summary),
        "open_risks": _format_prompt_value(state.open_risks),
        "implementation_plan_path": _format_prompt_value(state.implementation_plan_path),
        "planned_change_summary": _format_prompt_value(state.planned_change_summary),
        "verification_plan": _format_prompt_value(state.verification_plan),
        "implementation_summary": _format_prompt_value(state.implementation_summary),
        "changed_paths": _format_prompt_value(state.changed_paths),
        "submission_test_output": _format_prompt_value(state.submission_test_output),
        "submission_test_exit_code": _format_prompt_value(state.submission_test_exit_code),
        "review_summary": _format_prompt_value(state.review_summary),
        "review_findings": _format_prompt_value(state.review_findings),
        "knowledge_base_update_summary": _format_prompt_value(state.knowledge_base_update_summary),
        "knowledge_base_artifacts": _format_prompt_value(state.knowledge_base_artifacts),
        "blocked_cycle_next_lead": _format_prompt_value(state.blocked_cycle_next_lead),
        "goal": _format_prompt_value(task_input_values.get("goal")),
        "baseline_cycles": _format_prompt_value(task_input_values.get("baseline_cycles")),
        "repo_root": _format_prompt_value(context_values.get("repo_root")),
        }
    )
    return context


def _format_prompt_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _format_prompt_list(value) -> str:
    if not isinstance(value, list):
        return "- none"
    items = [str(item).strip() for item in value if str(item).strip()]
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def run_transition_preview(
    *,
    state: workflow_state.PerformanceOptimizationCycleWorkflowState,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> GraphBuilderPreviewResult:
    return asyncio.run(
        WORKFLOW_GRAPH.run(
            state=state,
            inputs=GraphBuilderPreviewInputs(
                current_step_id=current_step_id,
                observation=observation,
                verifier_result=verifier_result,
            ),
        )
    )


def run_start_preview(
    *,
    state: workflow_state.PerformanceOptimizationCycleWorkflowState,
    run_id: str,
    workflow_id: str,
    workflow_version: str,
) -> YieldResponse:
    return asyncio.run(
        START_GRAPH.run(
            state=state,
            inputs=GraphBuilderStartInputs(
                run_id=run_id,
                workflow_id=workflow_id,
                workflow_version=workflow_version,
            ),
        )
    )
