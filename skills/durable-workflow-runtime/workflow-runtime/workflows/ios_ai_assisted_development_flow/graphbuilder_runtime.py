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
    "run_brainstorming": NodeDefinition(
        step_id="run_brainstorming",
        prompt_asset_path=PROMPTS_DIR / "run_brainstorming.md",
        intent="clarify_and_prepare_design",
        expected_artifact="a brainstorming design package with a written design document path that is ready for subagent review authorization",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "approve_subagent_review": NodeDefinition(
        step_id="approve_subagent_review",
        prompt_asset_path=PROMPTS_DIR / "approve_subagent_review.md",
        intent="authorize_subagent_spec_review",
        expected_artifact="an explicit user authorization decision for the required subagent design review",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_spec_review": NodeDefinition(
        step_id="run_spec_review",
        prompt_asset_path=PROMPTS_DIR / "run_spec_review.md",
        intent="complete_subagent_spec_review_loop",
        expected_artifact="a review-complete design package with concrete subagent review artifacts and implementation-planning readiness",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "write_implementation_plan": NodeDefinition(
        step_id="write_implementation_plan",
        prompt_asset_path=PROMPTS_DIR / "write_implementation_plan.md",
        intent="create_superpowers_implementation_plan",
        expected_artifact="implementation plan document and recorded subagent-driven execution mode ready for implementation",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "execute_implementation": NodeDefinition(
        step_id="execute_implementation",
        prompt_asset_path=PROMPTS_DIR / "execute_implementation.md",
        intent="execute_superpowers_plan",
        expected_artifact="implemented plan tasks with verification evidence and any required planning follow-up",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_agentic_release_qa": NodeDefinition(
        step_id="run_agentic_release_qa",
        prompt_asset_path=PROMPTS_DIR / "run_agentic_release_qa.md",
        intent="run_change_aware_release_qa",
        expected_artifact="change-aware release QA verdict with executed checks, blocked checks, and risk-based next steps",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "request_pre_merge_code_review": NodeDefinition(
        step_id="request_pre_merge_code_review",
        prompt_asset_path=PROMPTS_DIR / "request_pre_merge_code_review.md",
        intent="request_pre_merge_code_review",
        expected_artifact="pre-merge code review findings and merge-readiness decision for the current local diff",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "verify_completion": NodeDefinition(
        step_id="verify_completion",
        prompt_asset_path=PROMPTS_DIR / "verify_completion.md",
        intent="verify_completion_before_final_delivery",
        expected_artifact="fresh completion verification evidence proving the workflow is ready to claim success",
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
    "finalize_delivery_summary": NodeDefinition(
        step_id="finalize_delivery_summary",
        prompt_asset_path=PROMPTS_DIR / "finalize_delivery_summary.md",
        intent="finalize_summary",
        expected_artifact="final user-facing summary",
        resume_instructions="No further resume.",
        final=True,
        done_when=("Output the final workflow summary",),
    ),
}


BUILDER = GraphBuilder(
    name="ios_ai_assisted_development_flow_graphbuilder_runtime",
    state_type=workflow_state.IosAiAssistedDevelopmentFlowWorkflowState,
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
    name="ios_ai_assisted_development_flow_graphbuilder_runtime_start",
    state_type=workflow_state.IosAiAssistedDevelopmentFlowWorkflowState,
    input_type=GraphBuilderStartInputs,
    output_type=YieldResponse,
    auto_instrument=False,
)


@START_BUILDER.step(node_id="emit_run_brainstorming")
async def emit_run_brainstorming(ctx) -> YieldResponse:
    node_definition = get_node_definition("run_brainstorming")
    contract = workflow_contract.get_step_contract("run_brainstorming")
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


START_BUILDER.add_edge(START_BUILDER.start_node, emit_run_brainstorming)
START_BUILDER.add_edge(emit_run_brainstorming, START_BUILDER.end_node)


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
    repair_context_value = getattr(state, "repair_context", {})
    repair_context = repair_context_value if isinstance(repair_context_value, dict) else {}
    repair_payload = repair_context.get("repair_payload")
    if not isinstance(repair_payload, dict):
        repair_payload = {}
    context = _template_context_from_state(state)
    context.update(
        {
            "current_step_id": step_id,
            "return_stage_id": getattr(state, "return_stage_id", None) or "",
            "source_stage_id": str(repair_context.get("source_stage_id") or ""),
            "repair_category": _format_prompt_value(
                getattr(state, "repair_category", None)
                or repair_context.get("repair_category")
                or repair_payload.get("category")
            ),
            "repair_summary": _format_prompt_value(
                getattr(state, "repair_summary", None)
                or repair_context.get("repair_summary")
                or repair_payload.get("summary")
            ),
            "repair_requirements": _format_prompt_list(
                getattr(state, "repair_requirements", None)
                or repair_context.get("repair_requirements")
                or repair_payload.get("requirements")
            ),
            "repair_evidence": _format_prompt_list(
                getattr(state, "repair_evidence", None)
                or repair_context.get("repair_evidence")
                or repair_payload.get("evidence")
            ),

            "terminal_reason": str(getattr(run_state, "terminal_reason", "") or ""),
            "degraded": str(
                bool(getattr(run_state, "artifacts_degraded", False))
                or str(getattr(run_state, "terminal_reason", "") or "") == "max_steps_exceeded"
            ).lower(),
        }
    )
    return context


def _template_context_from_state(state: workflow_state.IosAiAssistedDevelopmentFlowWorkflowState) -> dict:
    task_input_value = getattr(state, "task_input", {})
    context_value = getattr(state, "context", {})
    constraints_value = getattr(state, "constraints", {})
    task_input_values = task_input_value if isinstance(task_input_value, dict) else {}
    context_values = context_value if isinstance(context_value, dict) else {}
    constraint_values = constraints_value if isinstance(constraints_value, dict) else {}
    context = {
        "workflow_goal": getattr(state, "workflow_goal", None) or "",
        "task_input_json": json.dumps(task_input_values, ensure_ascii=False, indent=2),
        "context_json": json.dumps(context_values, ensure_ascii=False, indent=2),
        "constraints_json": json.dumps(constraint_values, ensure_ascii=False, indent=2),
    }
    context.update(
        {
        "artifacts_by_stage_json": json.dumps(getattr(state, "artifacts_by_stage", {}), ensure_ascii=False, indent=2),
        "clarification_questions": _format_prompt_value(getattr(state, 'clarification_questions', None)),
        "clarification_answers_summary": _format_prompt_value(getattr(state, 'clarification_answers_summary', None)),
        "design_summary": _format_prompt_value(getattr(state, 'design_summary', None)),
        "design_path": _format_prompt_value(getattr(state, 'design_path', None)),
        "ui_surface_affected": _format_prompt_value(getattr(state, 'ui_surface_affected', None)),
        "visual_spec_detail_summary": _format_prompt_value(getattr(state, 'visual_spec_detail_summary', None)),
        "design_comparison_source": _format_prompt_value(getattr(state, 'design_comparison_source', None)),
        "runtime_visual_comparison_scope": _format_prompt_value(getattr(state, 'runtime_visual_comparison_scope', None)),
        "open_questions": _format_prompt_value(getattr(state, 'open_questions', None)),
        "ready_for_subagent_review": _format_prompt_value(getattr(state, 'ready_for_subagent_review', None)),
        "subagent_review_approved": _format_prompt_value(getattr(state, 'subagent_review_approved', None)),
        "authorization_summary": _format_prompt_value(getattr(state, 'authorization_summary', None)),
        "ready_for_spec_review": _format_prompt_value(getattr(state, 'ready_for_spec_review', None)),
        "spec_review_perspectives": _format_prompt_value(getattr(state, 'spec_review_perspectives', None)),
        "spec_review_findings_summary": _format_prompt_value(getattr(state, 'spec_review_findings_summary', None)),
        "spec_review_subagent_summaries": _format_prompt_value(getattr(state, 'spec_review_subagent_summaries', None)),
        "spec_review_artifact_paths": _format_prompt_value(getattr(state, 'spec_review_artifact_paths', None)),
        "ready_for_planning": _format_prompt_value(getattr(state, 'ready_for_planning', None)),
        "plan_summary": _format_prompt_value(getattr(state, 'plan_summary', None)),
        "plan_path": _format_prompt_value(getattr(state, 'plan_path', None)),
        "execution_mode": _format_prompt_value(getattr(state, 'execution_mode', None)),
        "plan_revision_reason": _format_prompt_value(getattr(state, 'plan_revision_reason', None)),
        "ready_for_implementation": _format_prompt_value(getattr(state, 'ready_for_implementation', None)),
        "implementation_summary": _format_prompt_value(getattr(state, 'implementation_summary', None)),
        "implementation_completed_tasks": _format_prompt_value(getattr(state, 'implementation_completed_tasks', None)),
        "implementation_remaining_tasks": _format_prompt_value(getattr(state, 'implementation_remaining_tasks', None)),
        "changed_files": _format_prompt_value(getattr(state, 'changed_files', None)),
        "verification_commands": _format_prompt_value(getattr(state, 'verification_commands', None)),
        "open_issues": _format_prompt_value(getattr(state, 'open_issues', None)),
        "debugging_summary": _format_prompt_value(getattr(state, 'debugging_summary', None)),
        "implementation_verification_passed": _format_prompt_value(getattr(state, 'implementation_verification_passed', None)),
        "implementation_plan_updates_required": _format_prompt_value(getattr(state, 'implementation_plan_updates_required', None)),
        "plan_update_summary": _format_prompt_value(getattr(state, 'plan_update_summary', None)),
        "tasks_completed": _format_prompt_value(getattr(state, 'tasks_completed', None)),
        "release_qa_verdict": _format_prompt_value(getattr(state, 'release_qa_verdict', None)),
        "release_qa_summary": _format_prompt_value(getattr(state, 'release_qa_summary', None)),
        "release_qa_executed_checks": _format_prompt_value(getattr(state, 'release_qa_executed_checks', None)),
        "release_qa_blocked_checks": _format_prompt_value(getattr(state, 'release_qa_blocked_checks', None)),
        "release_qa_risk_next_steps": _format_prompt_value(getattr(state, 'release_qa_risk_next_steps', None)),
        "release_qa_artifacts": _format_prompt_value(getattr(state, 'release_qa_artifacts', None)),
        "release_qa_target_scope": _format_prompt_value(getattr(state, 'release_qa_target_scope', None)),
        "agent_device_status": _format_prompt_value(getattr(state, 'agent_device_status', None)),
        "agent_device_commands": _format_prompt_value(getattr(state, 'agent_device_commands', None)),
        "agent_device_artifacts": _format_prompt_value(getattr(state, 'agent_device_artifacts', None)),
        "agent_device_session": _format_prompt_value(getattr(state, 'agent_device_session', None)),
        "agent_device_replay_suite": _format_prompt_value(getattr(state, 'agent_device_replay_suite', None)),
        "agent_device_cli_version": _format_prompt_value(getattr(state, 'agent_device_cli_version', None)),
        "agent_device_observed_device": _format_prompt_value(getattr(state, 'agent_device_observed_device', None)),
        "agent_device_observed_app_id": _format_prompt_value(getattr(state, 'agent_device_observed_app_id', None)),
        "agent_device_runner_status": _format_prompt_value(getattr(state, 'agent_device_runner_status', None)),
        "agent_device_execution_receipt": _format_prompt_value(getattr(state, 'agent_device_execution_receipt', None)),
        "review_status": _format_prompt_value(getattr(state, 'review_status', None)),
        "reviewed_snapshot": _format_prompt_value(getattr(state, 'reviewed_snapshot', None)),
        "review_findings": _format_prompt_value(getattr(state, 'review_findings', None)),
        "review_summary": _format_prompt_value(getattr(state, 'review_summary', None)),
        "changes_requested": _format_prompt_value(getattr(state, 'changes_requested', None)),
        "completion_verification_passed": _format_prompt_value(getattr(state, 'completion_verification_passed', None)),
        "completion_verification_summary": _format_prompt_value(getattr(state, 'completion_verification_summary', None)),
        "completion_verification_evidence": _format_prompt_value(getattr(state, 'completion_verification_evidence', None)),
        "completion_remaining_risks": _format_prompt_value(getattr(state, 'completion_remaining_risks', None)),
        "completion_release_qa_risks_resolved": _format_prompt_value(getattr(state, 'completion_release_qa_risks_resolved', None)),
        "completion_release_qa_risk_resolution_summary": _format_prompt_value(getattr(state, 'completion_release_qa_risk_resolution_summary', None)),
        "terminal_reason": _format_prompt_value(getattr(state, 'terminal_reason', None)),
        "unblocking_blocking_reason": _format_prompt_value(getattr(state, 'unblocking_blocking_reason', None)),
        "unblocking_user_action_needed": _format_prompt_value(getattr(state, 'unblocking_user_action_needed', None)),
        "unblocking_suggested_next_input": _format_prompt_value(getattr(state, 'unblocking_suggested_next_input', None)),
        "repair_blocked_attempts": _format_prompt_value(getattr(state, 'repair_blocked_attempts', None)),
        "goal": _format_prompt_value(task_input_values.get("goal")),
        "preferred_change_name": _format_prompt_value(task_input_values.get("preferred_change_name")),
        "repo_root": _format_prompt_value(context_values.get("repo_root")),
        "source_doc_url": _format_prompt_value(context_values.get("source_doc_url")),
        "source_skill_url": _format_prompt_value(context_values.get("source_skill_url")),
        "agent_device_mode": _format_prompt_value(context_values.get("agent_device_mode")),
        "agent_device_app_id": _format_prompt_value(context_values.get("agent_device_app_id")),
        "agent_device_artifact_path": _format_prompt_value(context_values.get("agent_device_artifact_path")),
        "agent_device_device": _format_prompt_value(context_values.get("agent_device_device")),
        "agent_device_evidence_dir": _format_prompt_value(context_values.get("agent_device_evidence_dir")),
        "agent_device_expected_version": _format_prompt_value(context_values.get("agent_device_expected_version")),
        "max_steps": _format_prompt_value(constraint_values.get("max_steps")),
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
    state: workflow_state.IosAiAssistedDevelopmentFlowWorkflowState,
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
    state: workflow_state.IosAiAssistedDevelopmentFlowWorkflowState,
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
