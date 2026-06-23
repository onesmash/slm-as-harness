from __future__ import annotations

import asyncio
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
    "run_primary_stage": NodeDefinition(
        step_id="run_primary_stage",
        prompt_asset_path=PROMPTS_DIR / "run_primary_stage.md",
        intent="run_primary_stage",
        expected_artifact="primary workflow artifact summary",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "request_unblocking_input": NodeDefinition(
        step_id="request_unblocking_input",
        prompt_asset_path=PROMPTS_DIR / "request_unblocking_input.md",
        intent="request_unblocking_input",
        expected_artifact="user action needed to unblock the workflow",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "repair_and_resume": NodeDefinition(
        step_id="repair_and_resume",
        prompt_asset_path=PROMPTS_DIR / "repair_and_resume.md",
        intent="repair_and_resume",
        expected_artifact="repair actions needed before returning to the original stage",
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
    name="example_workflow_graphbuilder_runtime",
    state_type=workflow_state.ExampleWorkflowState,
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
    name="example_workflow_graphbuilder_runtime_start",
    state_type=workflow_state.ExampleWorkflowState,
    input_type=GraphBuilderStartInputs,
    output_type=YieldResponse,
    auto_instrument=False,
)


@START_BUILDER.step(node_id="emit_run_primary_stage")
async def emit_run_primary_stage(ctx) -> YieldResponse:
    node_definition = get_node_definition("run_primary_stage")
    contract = workflow_contract.get_step_contract("run_primary_stage")
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
            "workflow_goal": ctx.state.workflow_goal or "",
        },
    )
    return YieldResponse(
        run_id=ctx.inputs.run_id,
        step_id=node_definition.step_id,
        prompt_envelope=prompt_envelope,
    )


START_BUILDER.add_edge(START_BUILDER.start_node, emit_run_primary_stage)
START_BUILDER.add_edge(emit_run_primary_stage, START_BUILDER.end_node)


START_GRAPH = START_BUILDER.build()


def build_graph() -> Graph:
    return WORKFLOW_GRAPH


def build_start_graph() -> Graph:
    return START_GRAPH


def get_node_definition(node_key: str) -> NodeDefinition:
    try:
        return NODE_DEFINITIONS[node_key]
    except KeyError as exc:  # pragma: no cover - template usage path
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
        "workflow_goal": state.workflow_goal or "",
        "current_step_id": step_id,
        "return_stage_id": state.return_stage_id or "",
        "repair_category": str(repair_payload.get("category") or ""),
        "repair_summary": str(repair_payload.get("summary") or ""),
        "repair_requirements": _format_prompt_list(repair_payload.get("requirements")),
        "repair_evidence": _format_prompt_list(repair_payload.get("evidence")),
    }


def _format_prompt_list(value) -> str:
    if not isinstance(value, list):
        return "- none"
    items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def run_transition_preview(
    *,
    state: workflow_state.ExampleWorkflowState,
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
    state: workflow_state.ExampleWorkflowState,
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
