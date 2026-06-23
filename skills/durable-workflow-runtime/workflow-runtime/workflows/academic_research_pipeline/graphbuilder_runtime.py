from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_graph.graph_builder import Graph, GraphBuilder

from runtime.models import HistoryEntry, YieldResponse
from workflows.academic_research_pipeline import contract as workflow_contract
from workflows.academic_research_pipeline import policy, state as workflow_state
from workflows.common.policies import TransitionDecision
from workflows.common.prompting import build_prompt_envelope, resolve_prompt_asset

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
    "collect_research_context": NodeDefinition(
        step_id="collect_research_context",
        prompt_asset_path=PROMPTS_DIR / "collect_research_context.md",
        intent="collect_research_context",
        expected_artifact="academic research materials and entry-stage context",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "plan_academic_pipeline": NodeDefinition(
        step_id="plan_academic_pipeline",
        prompt_asset_path=PROMPTS_DIR / "plan_academic_pipeline.md",
        intent="plan_academic_pipeline",
        expected_artifact="ARS stage plan and checkpoint policy",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_research_stage": NodeDefinition(
        step_id="run_research_stage",
        prompt_asset_path=PROMPTS_DIR / "run_research_stage.md",
        intent="run_research_stage",
        expected_artifact="Stage 1 research artifacts ready for writing",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_write_stage": NodeDefinition(
        step_id="run_write_stage",
        prompt_asset_path=PROMPTS_DIR / "run_write_stage.md",
        intent="run_write_stage",
        expected_artifact="Stage 2 draft and writing artifacts ready for integrity",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_pre_review_integrity": NodeDefinition(
        step_id="run_pre_review_integrity",
        prompt_asset_path=PROMPTS_DIR / "run_pre_review_integrity.md",
        intent="run_pre_review_integrity",
        expected_artifact="Stage 2.5 integrity report and Material Passport",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_review_stage": NodeDefinition(
        step_id="run_review_stage",
        prompt_asset_path=PROMPTS_DIR / "run_review_stage.md",
        intent="run_review_stage",
        expected_artifact="Stage 3 peer review package and editorial decision",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_revision_stage": NodeDefinition(
        step_id="run_revision_stage",
        prompt_asset_path=PROMPTS_DIR / "run_revision_stage.md",
        intent="run_revision_stage",
        expected_artifact="Stage 4 revised draft and response artifacts",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_rereview_stage": NodeDefinition(
        step_id="run_rereview_stage",
        prompt_asset_path=PROMPTS_DIR / "run_rereview_stage.md",
        intent="run_rereview_stage",
        expected_artifact="Stage 3' re-review package and residual issue decision",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "run_final_integrity": NodeDefinition(
        step_id="run_final_integrity",
        prompt_asset_path=PROMPTS_DIR / "run_final_integrity.md",
        intent="run_final_integrity",
        expected_artifact="Stage 4.5 final integrity evidence",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "finalize_publication_package": NodeDefinition(
        step_id="finalize_publication_package",
        prompt_asset_path=PROMPTS_DIR / "finalize_publication_package.md",
        intent="finalize_publication_package",
        expected_artifact="Stage 5 publication-ready output package",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "generate_process_summary": NodeDefinition(
        step_id="generate_process_summary",
        prompt_asset_path=PROMPTS_DIR / "generate_process_summary.md",
        intent="generate_process_summary",
        expected_artifact="Stage 6 process summary and collaboration review",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "request_unblocking_input": NodeDefinition(
        step_id="request_unblocking_input",
        prompt_asset_path=PROMPTS_DIR / "request_unblocking_input.md",
        intent="request_unblocking_input",
        expected_artifact="user action needed to unblock the academic workflow",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "repair_and_resume": NodeDefinition(
        step_id="repair_and_resume",
        prompt_asset_path=PROMPTS_DIR / "repair_and_resume.md",
        intent="repair_and_resume",
        expected_artifact="repair actions needed before returning to the ARS stage",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "finalize_summary": NodeDefinition(
        step_id="finalize_summary",
        prompt_asset_path=PROMPTS_DIR / "finalize_summary.md",
        intent="finalize_summary",
        expected_artifact="final user-facing summary",
        resume_instructions="No further resume.",
        final=True,
        done_when=("输出最终总结",),
    ),
}


BUILDER = GraphBuilder(
    name="academic_research_pipeline_graphbuilder_runtime",
    state_type=workflow_state.AcademicResearchPipelineState,
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
    name="academic_research_pipeline_graphbuilder_runtime_start",
    state_type=workflow_state.AcademicResearchPipelineState,
    input_type=GraphBuilderStartInputs,
    output_type=YieldResponse,
    auto_instrument=False,
)


@START_BUILDER.step(node_id="emit_collect_research_context")
async def emit_collect_research_context(ctx) -> YieldResponse:
    node_definition = get_node_definition("collect_research_context")
    contract = workflow_contract.get_step_contract("collect_research_context")
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
        template_context={
            "research_goal": ctx.state.research_goal or "",
        },
    )
    return YieldResponse(
        run_id=ctx.inputs.run_id,
        step_id=node_definition.step_id,
        prompt_envelope=prompt_envelope,
    )


START_BUILDER.add_edge(START_BUILDER.start_node, emit_collect_research_context)
START_BUILDER.add_edge(emit_collect_research_context, START_BUILDER.end_node)
START_GRAPH = START_BUILDER.build()


def build_graph() -> Graph:
    return WORKFLOW_GRAPH


def build_start_graph() -> Graph:
    return START_GRAPH


def get_node_definition(node_key: str) -> NodeDefinition:
    try:
        return NODE_DEFINITIONS[node_key]
    except KeyError as exc:  # pragma: no cover - guarded by workflow policy
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
    return {
        "research_goal": state.research_goal or "",
        "entry_stage": state.entry_stage or "",
        "next_stage": state.next_stage or "",
        "current_step_id": step_id,
        "available_materials": _format_materials(state.available_materials),
        "stage_plan": _format_stage_plan(state.stage_plan),
        "mode_selection": _format_mapping(state.mode_selection),
        "paper_path": state.paper_path or "",
        "draft_path": state.draft_path or "",
        "material_passport_path": state.material_passport_path or "",
        "research_artifact_paths": _format_prompt_list(state.research_artifact_paths),
        "review_package_path": state.review_package_path or "",
        "revision_roadmap_path": state.revision_roadmap_path or "",
        "revised_draft_path": state.revised_draft_path or "",
        "rereview_package_path": state.rereview_package_path or "",
        "final_integrity_report_path": state.final_integrity_report_path or "",
        "output_package_paths": _format_prompt_list(state.output_package_paths),
        "process_summary_path": state.process_summary_path or "",
        "editorial_decision": state.editorial_decision or "",
        "rereview_decision": state.rereview_decision or "",
        "integrity_passed": _format_optional_bool(state.integrity_passed),
        "final_integrity_passed": _format_optional_bool(state.final_integrity_passed),
        "revision_loop_count": str(state.revision_loop_count),
        "max_revision_loops": str(state.max_revision_loops),
        "source_materials_path": state.source_materials_path or "",
        "output_dir": state.output_dir or "",
        "require_user_checkpoints": str(state.require_user_checkpoints),
        "enable_claim_audit": str(state.enable_claim_audit),
        "allow_format_render": str(state.allow_format_render),
        "return_stage_id": state.return_stage_id or "",
        "source_stage_id": str(repair_context.get("source_stage_id", "")),
        "repair_category": str(repair_payload.get("category", "")),
        "repair_summary": str(repair_payload.get("summary", "")),
        "repair_requirements": _format_prompt_list(repair_payload.get("requirements")),
        "repair_evidence": _format_prompt_list(repair_payload.get("evidence")),
    }


def _format_prompt_list(value) -> str:
    if not isinstance(value, list):
        return "- 无"
    items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if not items:
        return "- 无"
    return "\n".join(f"- {item}" for item in items)


def _format_materials(value) -> str:
    if not isinstance(value, list) or not value:
        return "- 尚未收集"
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("path") or "material")
        kind = str(item.get("type") or "unknown")
        lines.append(f"- {name} ({kind})")
    return "\n".join(lines) if lines else "- 尚未收集"


def _format_stage_plan(value) -> str:
    if not isinstance(value, list) or not value:
        return "- 尚未规划"
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        stage = str(item.get("stage") or item.get("id") or "stage")
        action = str(item.get("action") or item.get("mode") or "")
        gate = str(item.get("gate") or "")
        detail = " / ".join(part for part in (action, gate) if part)
        lines.append(f"- {stage}: {detail}" if detail else f"- {stage}")
    return "\n".join(lines) if lines else "- 尚未规划"


def _format_mapping(value: dict[str, object]) -> str:
    if not isinstance(value, dict) or not value:
        return "- 无"
    return "\n".join(f"- {key}: {value[key]}" for key in sorted(value))


def _format_issue_list(value) -> str:
    if not isinstance(value, list):
        return "- 无"
    lines: list[str] = []
    for item in value:
        if isinstance(item, dict):
            summary = str(item.get("summary") or item.get("issue") or item)
            severity = str(item.get("severity") or "").strip()
            lines.append(f"- [{severity}] {summary}" if severity else f"- {summary}")
        elif isinstance(item, str) and item.strip():
            lines.append(f"- {item.strip()}")
    return "\n".join(lines) if lines else "- 无"


def _format_optional_bool(value: bool | None) -> str:
    return "" if value is None else str(value)


def run_transition_preview(
    *,
    state: workflow_state.AcademicResearchPipelineState,
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
    state: workflow_state.AcademicResearchPipelineState,
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
