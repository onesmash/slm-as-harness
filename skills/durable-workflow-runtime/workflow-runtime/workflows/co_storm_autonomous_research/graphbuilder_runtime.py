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
    "warm_start_shared_space": NodeDefinition(
        step_id="warm_start_shared_space",
        prompt_asset_path=PROMPTS_DIR / "warm_start_shared_space.md",
        intent="seed_a_shared_conceptual_space",
        expected_artifact="initial expert roster with stable expert identifiers, perspective-guided research transcript, evidence registry, and seeded knowledge map",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "launch_expert_subagents": NodeDefinition(
        step_id="launch_expert_subagents",
        prompt_asset_path=PROMPTS_DIR / "launch_expert_subagents.md",
        intent="launch_independent_expert_subagents",
        expected_artifact="parallel independent expert-subagent run manifest, one grounded result per expert, and repository-relative result artifacts",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "autonomous_roundtable": NodeDefinition(
        step_id="autonomous_roundtable",
        prompt_asset_path=PROMPTS_DIR / "autonomous_roundtable.md",
        intent="advance_one_moderated_expert_round",
        expected_artifact="one Moderator synthesis turn over independent expert-subagent results, updated evidence and coverage, and an exclusive routing decision",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "reorganize_knowledge_space": NodeDefinition(
        step_id="reorganize_knowledge_space",
        prompt_asset_path=PROMPTS_DIR / "reorganize_knowledge_space.md",
        intent="reorganize_the_shared_knowledge_map",
        expected_artifact="expanded, deduplicated, and coverage-aware knowledge-map summary",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "synthesize_report": NodeDefinition(
        step_id="synthesize_report",
        prompt_asset_path=PROMPTS_DIR / "synthesize_report.md",
        intent="synthesize_the_cited_report",
        expected_artifact="structured report file with sections, inline citations, and a report summary",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "verify_report": NodeDefinition(
        step_id="verify_report",
        prompt_asset_path=PROMPTS_DIR / "verify_report.md",
        intent="verify_report_quality_and_citation_integrity",
        expected_artifact="independent report quality verdict, citation coverage summary, and repair findings if needed",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "repair_report": NodeDefinition(
        step_id="repair_report",
        prompt_asset_path=PROMPTS_DIR / "repair_report.md",
        intent="repair_report_quality_or_grounding",
        expected_artifact="concrete report repair actions and a repaired-report handoff",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "request_unblocking_input": NodeDefinition(
        step_id="request_unblocking_input",
        prompt_asset_path=PROMPTS_DIR / "request_unblocking_input.md",
        intent="request_unblocking_input",
        expected_artifact='host-visible external-block diagnostic (compatibility fallback only)',
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "repair_and_resume": NodeDefinition(
        step_id="repair_and_resume",
        prompt_asset_path=PROMPTS_DIR / "repair_and_resume.md",
        intent="repair_and_resume",
        expected_artifact='repair actions needed before returning to the original stage',
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "finalize_collaborative_report": NodeDefinition(
        step_id="finalize_collaborative_report",
        prompt_asset_path=PROMPTS_DIR / "finalize_collaborative_report.md",
        intent="finalize_summary",
        expected_artifact="final user-facing summary",
        resume_instructions="No further resume.",
        final=True,
        done_when=("Output the final workflow summary",),
    ),
}


BUILDER = GraphBuilder(
    name="co_storm_autonomous_research_graphbuilder_runtime",
    state_type=workflow_state.CoStormAutonomousResearchWorkflowState,
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
    name="co_storm_autonomous_research_graphbuilder_runtime_start",
    state_type=workflow_state.CoStormAutonomousResearchWorkflowState,
    input_type=GraphBuilderStartInputs,
    output_type=YieldResponse,
    auto_instrument=False,
)


@START_BUILDER.step(node_id="emit_warm_start_shared_space")
async def emit_warm_start_shared_space(ctx) -> YieldResponse:
    node_definition = get_node_definition("warm_start_shared_space")
    contract = workflow_contract.get_step_contract("warm_start_shared_space")
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


START_BUILDER.add_edge(START_BUILDER.start_node, emit_warm_start_shared_space)
START_BUILDER.add_edge(emit_warm_start_shared_space, START_BUILDER.end_node)


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


def _template_context_from_state(state: workflow_state.CoStormAutonomousResearchWorkflowState) -> dict:
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
        "expert_roster": _format_prompt_value(state.expert_roster),
        "conversation_transcript": _format_prompt_value(state.conversation_transcript),
        "knowledge_map_summary": _format_prompt_value(state.knowledge_map_summary),
        "evidence_registry": _format_prompt_value(state.evidence_registry),
        "coverage_map": _format_prompt_value(state.coverage_map),
        "round_index": _format_prompt_value(state.round_index),
        "fanout_round_index": _format_prompt_value(state.fanout_round_index),
        "subagent_expert_ids": _format_prompt_value(state.subagent_expert_ids),
        "subagent_run_ids": _format_prompt_value(state.subagent_run_ids),
        "subagent_result_summaries": _format_prompt_value(state.subagent_result_summaries),
        "subagent_artifact_paths": _format_prompt_value(state.subagent_artifact_paths),
        "subagent_binding_records": _format_prompt_value(state.subagent_binding_records),
        "subagent_run_history": _format_prompt_value(state.subagent_run_history),
        "subagent_attempt_history": _format_prompt_value(state.subagent_attempt_history),
        "current_fanout_attempt": _format_prompt_value(state.current_fanout_attempt),
        "fanout_complete": _format_prompt_value(state.fanout_complete),
        "last_turn_summary": _format_prompt_value(state.last_turn_summary),
        "round_decision": _format_prompt_value(state.round_decision),
        "coverage_sufficient": _format_prompt_value(state.coverage_sufficient),
        "ready_for_report": _format_prompt_value(state.ready_for_report),
        "reorganization_summary": _format_prompt_value(state.reorganization_summary),
        "reorganization_count": _format_prompt_value(state.reorganization_count),
        "outline": _format_prompt_value(state.outline),
        "report_path": _format_prompt_value(state.report_path),
        "report_summary": _format_prompt_value(state.report_summary),
        "report_sections": _format_prompt_value(state.report_sections),
        "quality_verdict": _format_prompt_value(state.quality_verdict),
        "quality_findings": _format_prompt_value(state.quality_findings),
        "citation_coverage_summary": _format_prompt_value(state.citation_coverage_summary),
        "report_ready": _format_prompt_value(state.report_ready),
        "verified_report_path": _format_prompt_value(state.verified_report_path),
        "report_repair_summary": _format_prompt_value(state.report_repair_summary),
        "repair_actions": _format_prompt_value(state.repair_actions),
        "goal": _format_prompt_value(task_input_values.get("goal")),
        "deliverable_type": _format_prompt_value(task_input_values.get("deliverable_type")),
        "research_scope": _format_prompt_value(task_input_values.get("research_scope")),
        "source_policy": _format_prompt_value(task_input_values.get("source_policy")),
        "repo_root": _format_prompt_value(context_values.get("repo_root")),
        "source_materials_path": _format_prompt_value(context_values.get("source_materials_path")),
        "output_dir": _format_prompt_value(context_values.get("output_dir")),
        "max_steps": _format_prompt_value(constraint_values.get("max_steps")),
        "max_rounds": _format_prompt_value(constraint_values.get("max_rounds")),
        "min_evidence_items": _format_prompt_value(constraint_values.get("min_evidence_items")),
        "coverage_threshold": _format_prompt_value(constraint_values.get("coverage_threshold")),
        "max_reorganizations": _format_prompt_value(constraint_values.get("max_reorganizations")),
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
    state: workflow_state.CoStormAutonomousResearchWorkflowState,
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
    state: workflow_state.CoStormAutonomousResearchWorkflowState,
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
