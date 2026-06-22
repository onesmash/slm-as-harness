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
        intent="clarify_and_approve_design",
        expected_artifact="clarified requirements, approved brainstorming design document, and design document path",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "propose_openspec_change": NodeDefinition(
        step_id="propose_openspec_change",
        prompt_asset_path=PROMPTS_DIR / "propose_openspec_change.md",
        intent="create_openspec_change_artifacts",
        expected_artifact="OpenSpec proposal, design/spec, and tasks ready for implementation",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "refine_change_with_openspec": NodeDefinition(
        step_id="refine_change_with_openspec",
        prompt_asset_path=PROMPTS_DIR / "refine_change_with_openspec.md",
        intent="refine_formalized_change",
        expected_artifact="refined OpenSpec artifacts ready for task execution",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "approve_refine": NodeDefinition(
        step_id="approve_refine",
        prompt_asset_path=PROMPTS_DIR / "approve_refine.md",
        intent="confirm_refine_and_approve_implementation",
        expected_artifact="user approval to proceed from refinement to implementation",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "execute_implementation": NodeDefinition(
        step_id="execute_implementation",
        prompt_asset_path=PROMPTS_DIR / "execute_implementation.md",
        intent="implement_openspec_tasks",
        expected_artifact="completed OpenSpec task implementation with verification evidence",
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
    repair_context = state.repair_context if isinstance(state.repair_context, dict) else {}
    context = _template_context_from_state(state)
    context.update(
        {
            "current_step_id": step_id,
            "return_stage_id": state.return_stage_id or "",
            "source_stage_id": str(repair_context.get("source_stage_id") or ""),
            "repair_reason": str(repair_context.get("repair_reason") or ""),
            "repair_summary": str(repair_context.get("summary") or ""),
            "blocked_reason": str(repair_context.get("blocked_reason") or ""),
            "error_message": str(repair_context.get("error_message") or ""),
            "missing_inputs": _format_prompt_list(repair_context.get("missing_inputs")),
            "missing_artifacts": _format_prompt_list(repair_context.get("missing_artifacts")),
            "repair_failed_commands": _format_prompt_list(repair_context.get("failed_commands")),
            "repair_failing_checks": _format_prompt_value(repair_context.get("failing_checks")),
            "repair_details_json": _format_prompt_value(repair_context.get("details")),
        }
    )
    return context


def _template_context_from_state(state: workflow_state.IosAiAssistedDevelopmentFlowWorkflowState) -> dict:
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
        "clarification_questions": _format_prompt_value(state.clarification_questions),
        "clarification_answers_summary": _format_prompt_value(state.clarification_answers_summary),
        "approved_design_summary": _format_prompt_value(state.approved_design_summary),
        "approved_design_path": _format_prompt_value(state.approved_design_path),
        "ui_surface_affected": _format_prompt_value(state.ui_surface_affected),
        "design_comparison_source": _format_prompt_value(state.design_comparison_source),
        "runtime_visual_comparison_scope": _format_prompt_value(state.runtime_visual_comparison_scope),
        "spec_review_findings_summary": _format_prompt_value(state.spec_review_findings_summary),
        "open_questions": _format_prompt_value(state.open_questions),
        "change_name": _format_prompt_value(state.change_name),
        "change_path": _format_prompt_value(state.change_path),
        "proposal_path": _format_prompt_value(state.proposal_path),
        "openspec_design_path": _format_prompt_value(state.openspec_design_path),
        "tasks_path": _format_prompt_value(state.tasks_path),
        "spec_paths": _format_prompt_value(state.spec_paths),
        "refinement_summary": _format_prompt_value(state.refinement_summary),
        "refinement_user_discussion_summary": _format_prompt_value(state.refinement_user_discussion_summary),
        "changed_artifacts": _format_prompt_value(state.changed_artifacts),
        "unresolved_questions": _format_prompt_value(state.unresolved_questions),
        "refinement_user_approved": _format_prompt_value(state.refinement_user_approved),
        "refinement_user_feedback": _format_prompt_value(state.refinement_user_feedback),
        "implementation_summary": _format_prompt_value(state.implementation_summary),
        "changed_files": _format_prompt_value(state.changed_files),
        "verification_commands": _format_prompt_value(state.verification_commands),
        "open_issues": _format_prompt_value(state.open_issues),
        "release_qa_verdict": _format_prompt_value(state.release_qa_verdict),
        "release_qa_summary": _format_prompt_value(state.release_qa_summary),
        "release_qa_executed_checks": _format_prompt_value(state.release_qa_executed_checks),
        "release_qa_blocked_checks": _format_prompt_value(state.release_qa_blocked_checks),
        "release_qa_risk_next_steps": _format_prompt_value(state.release_qa_risk_next_steps),
        "release_qa_artifacts": _format_prompt_value(state.release_qa_artifacts),
        "review_status": _format_prompt_value(state.review_status),
        "reviewed_snapshot": _format_prompt_value(state.reviewed_snapshot),
        "review_findings": _format_prompt_value(state.review_findings),
        "review_summary": _format_prompt_value(state.review_summary),
        "missing_review_inputs": _format_prompt_value(state.missing_review_inputs),
        "completion_verification_passed": _format_prompt_value(state.completion_verification_passed),
        "completion_verification_summary": _format_prompt_value(state.completion_verification_summary),
        "completion_verification_evidence": _format_prompt_value(state.completion_verification_evidence),
        "completion_remaining_risks": _format_prompt_value(state.completion_remaining_risks),
        "completion_missing_verification_inputs": _format_prompt_value(state.completion_missing_verification_inputs),
        "completion_release_qa_risks_resolved": _format_prompt_value(state.completion_release_qa_risks_resolved),
        "completion_release_qa_risk_resolution_summary": _format_prompt_value(state.completion_release_qa_risk_resolution_summary),
        "goal": _format_prompt_value(task_input_values.get("goal")),
        "preferred_change_name": _format_prompt_value(task_input_values.get("preferred_change_name")),
        "repo_root": _format_prompt_value(context_values.get("repo_root")),
        "source_doc_url": _format_prompt_value(context_values.get("source_doc_url")),
        "source_skill_url": _format_prompt_value(context_values.get("source_skill_url")),
        "openspec_source_url": _format_prompt_value(context_values.get("openspec_source_url")),
        "max_steps": _format_prompt_value(constraint_values.get("max_steps")),
        "require_user_approval": _format_prompt_value(constraint_values.get("require_user_approval")),
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
