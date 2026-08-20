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
    "collect_earnings_packet": NodeDefinition(
        step_id="collect_earnings_packet",
        prompt_asset_path=PROMPTS_DIR / "collect_earnings_packet.md",
        intent="collect_earnings_packet",
        expected_artifact="earnings packet with reported actuals, consensus, filings, and the full call transcript",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "analyze_earnings_call": NodeDefinition(
        step_id="analyze_earnings_call",
        prompt_asset_path=PROMPTS_DIR / "analyze_earnings_call.md",
        intent="analyze_earnings_call",
        expected_artifact="call analysis covering beat/miss, guidance, tone, dodged questions, and thesis impact",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "update_coverage_model": NodeDefinition(
        step_id="update_coverage_model",
        prompt_asset_path=PROMPTS_DIR / "update_coverage_model.md",
        intent="update_coverage_model",
        expected_artifact="updated coverage model, variance table, and estimate-change summary",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "audit_coverage_model": NodeDefinition(
        step_id="audit_coverage_model",
        prompt_asset_path=PROMPTS_DIR / "audit_coverage_model.md",
        intent="audit_coverage_model",
        expected_artifact="model-scope Excel audit with no unresolved critical findings",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "repair_model_audit": NodeDefinition(
        step_id="repair_model_audit",
        prompt_asset_path=PROMPTS_DIR / "repair_model_audit.md",
        intent="repair_model_audit",
        expected_artifact="repaired coverage model ready to re-run the model-scope audit",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "draft_earnings_note": NodeDefinition(
        step_id="draft_earnings_note",
        prompt_asset_path=PROMPTS_DIR / "draft_earnings_note.md",
        intent="draft_earnings_note",
        expected_artifact="staged post-earnings note draft with variance table and call read",
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
    "finalize_earnings_review": NodeDefinition(
        step_id="finalize_earnings_review",
        prompt_asset_path=PROMPTS_DIR / "finalize_earnings_review.md",
        intent="finalize_summary",
        expected_artifact="final user-facing summary",
        resume_instructions="No further resume.",
        final=True,
        done_when=("Output the final workflow summary",),
    ),
}


BUILDER = GraphBuilder(
    name="earnings_reviewer_graphbuilder_runtime",
    state_type=workflow_state.EarningsReviewerWorkflowState,
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
    name="earnings_reviewer_graphbuilder_runtime_start",
    state_type=workflow_state.EarningsReviewerWorkflowState,
    input_type=GraphBuilderStartInputs,
    output_type=YieldResponse,
    auto_instrument=False,
)


@START_BUILDER.step(node_id="emit_collect_earnings_packet")
async def emit_collect_earnings_packet(ctx) -> YieldResponse:
    node_definition = get_node_definition("collect_earnings_packet")
    contract = workflow_contract.get_step_contract("collect_earnings_packet")
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


START_BUILDER.add_edge(START_BUILDER.start_node, emit_collect_earnings_packet)
START_BUILDER.add_edge(emit_collect_earnings_packet, START_BUILDER.end_node)


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
            "repair_blocked_attempts": _format_prompt_value(getattr(state, "repair_blocked_attempts", 0)),
            "terminal_reason": str(getattr(run_state, "terminal_reason", "") or ""),
            "degraded": str(
                bool(getattr(run_state, "artifacts_degraded", False))
                or str(getattr(run_state, "terminal_reason", "") or "") == "max_steps_exceeded"
            ).lower(),
        }
    )
    return context


def _template_context_from_state(state: workflow_state.EarningsReviewerWorkflowState) -> dict:
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
        "artifacts_by_stage_json": json.dumps(state.artifacts_by_stage, ensure_ascii=False, indent=2),
        "repair_requirements": _format_prompt_value(state.repair_requirements),
        "repair_evidence": _format_prompt_value(state.repair_evidence),
        "repair_transition_reason": _format_prompt_value(state.repair_transition_reason),
        "repair_blocked_attempts": _format_prompt_value(state.repair_blocked_attempts),
        "ticker": _format_prompt_value(state.ticker),
        "reporting_period": _format_prompt_value(state.reporting_period),
        "earnings_packet_path": _format_prompt_value(state.earnings_packet_path),
        "transcript_locator": _format_prompt_value(state.transcript_locator),
        "filings_inventory": _format_prompt_value(state.filings_inventory),
        "actuals_source": _format_prompt_value(state.actuals_source),
        "consensus_source": _format_prompt_value(state.consensus_source),
        "skip_note": _format_prompt_value(state.skip_note),
        "missing_packet_inputs": _format_prompt_value(state.missing_packet_inputs),
        "headline_read": _format_prompt_value(state.headline_read),
        "beat_miss_summary": _format_prompt_value(state.beat_miss_summary),
        "guidance_changes": _format_prompt_value(state.guidance_changes),
        "management_tone": _format_prompt_value(state.management_tone),
        "dodged_questions": _format_prompt_value(state.dodged_questions),
        "thesis_impact": _format_prompt_value(state.thesis_impact),
        "call_analysis_summary": _format_prompt_value(state.call_analysis_summary),
        "unsourced_flags": _format_prompt_value(state.unsourced_flags),
        "used_full_transcript": _format_prompt_value(state.used_full_transcript),
        "updated_model_path": _format_prompt_value(state.updated_model_path),
        "variance_metrics": _format_prompt_value(state.variance_metrics),
        "variance_rows": _format_prompt_value(state.variance_rows),
        "estimate_change_summary": _format_prompt_value(state.estimate_change_summary),
        "price_target_change": _format_prompt_value(state.price_target_change),
        "thesis_change_summary": _format_prompt_value(state.thesis_change_summary),
        "requires_model_builder_handoff": _format_prompt_value(state.requires_model_builder_handoff),
        "handoff_target": _format_prompt_value(state.handoff_target),
        "handoff_reason": _format_prompt_value(state.handoff_reason),
        "handoff_payload": _format_prompt_value(state.handoff_payload),
        "audit_summary": _format_prompt_value(state.audit_summary),
        "audit_findings": _format_prompt_value(state.audit_findings),
        "critical_finding_count": _format_prompt_value(state.critical_finding_count),
        "model_audit_repair_summary": _format_prompt_value(state.model_audit_repair_summary),
        "note_path": _format_prompt_value(state.note_path),
        "note_headline": _format_prompt_value(state.note_headline),
        "published_externally": _format_prompt_value(state.published_externally),
        "unblocking_blocking_reason": _format_prompt_value(state.unblocking_blocking_reason),
        "unblocking_user_action_needed": _format_prompt_value(state.unblocking_user_action_needed),
        "unblocking_suggested_next_input": _format_prompt_value(state.unblocking_suggested_next_input),
        "goal": _format_prompt_value(task_input_values.get("goal")),
        "repo_root": _format_prompt_value(context_values.get("repo_root")),
        "coverage_model_path": _format_prompt_value(context_values.get("coverage_model_path")),
        "transcript_path": _format_prompt_value(context_values.get("transcript_path")),
        "filings_path": _format_prompt_value(context_values.get("filings_path")),
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
    state: workflow_state.EarningsReviewerWorkflowState,
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
    state: workflow_state.EarningsReviewerWorkflowState,
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
