from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_graph.graph_builder import Graph, GraphBuilder

from runtime.models import HistoryEntry
from runtime.models import YieldResponse
from workflows.common.policies import TransitionDecision
from workflows.common.prompting import build_prompt_envelope, resolve_prompt_asset
from workflows.demo_prompt_loop import policy, state as workflow_state
from workflows.demo_prompt_loop import contract as workflow_contract

WORKFLOW_VERSION = "v1"
PROMPTS_DIR = Path(__file__).with_name("prompts")
SKILL_RUNTIME_ROOT = Path(__file__).resolve().parents[2]


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


@dataclass(frozen=True)
class GraphBuilderTransition:
    current_step_id: str
    decision: TransitionDecision

    def to_trace_payload(self) -> dict:
        return self.decision.to_trace_payload()


NODE_DEFINITIONS = {
    "collect_context": NodeDefinition(
        step_id="collect_context",
        prompt_asset_path=PROMPTS_DIR / "collect_context.md",
        intent="collect_context",
        expected_artifact="runtime scaffold status",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "request_missing_access": NodeDefinition(
        step_id="request_missing_access",
        prompt_asset_path=PROMPTS_DIR / "request_missing_access.md",
        intent="request_missing_access",
        expected_artifact="user action needed summary",
        resume_instructions="Return an Observation preserving run_id and step_id.",
    ),
    "recheck_runtime_scaffold": NodeDefinition(
        step_id="recheck_runtime_scaffold",
        prompt_asset_path=PROMPTS_DIR / "recheck_runtime_scaffold.md",
        intent="recheck_runtime_scaffold",
        expected_artifact="rechecked runtime scaffold status",
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
    name="demo_prompt_loop_graphbuilder_runtime",
    state_type=workflow_state.DemoGraphState,
    input_type=GraphBuilderPreviewInputs,
    output_type=GraphBuilderPreviewResult,
    auto_instrument=False,
)


@BUILDER.step(node_id="evaluate_transition")
async def evaluate_transition(
    ctx,
) -> GraphBuilderTransition:
    return GraphBuilderTransition(
        current_step_id=ctx.inputs.current_step_id,
        decision=policy.choose_next_node(
            current_step_id=ctx.inputs.current_step_id,
            state=workflow_state.serialize_state(ctx.state),
            observation=ctx.inputs.observation,
            verifier_result=ctx.inputs.verifier_result,
        ),
    )


@BUILDER.step(node_id="route_request_missing_access")
async def route_request_missing_access(
    ctx,
) -> GraphBuilderPreviewResult:
    trace_payload = ctx.inputs.to_trace_payload()
    return GraphBuilderPreviewResult(
        step_id="request_missing_access",
        branch_kind=ctx.inputs.decision.branch_kind,
        reason=ctx.inputs.decision.reason,
        trace_payload=trace_payload,
        history_entry=HistoryEntry.branch_selected(
            node=ctx.inputs.current_step_id,
            step_id=ctx.inputs.current_step_id,
            payload=trace_payload,
        ),
    )


@BUILDER.step(node_id="route_recheck_runtime_scaffold")
async def route_recheck_runtime_scaffold(
    ctx,
) -> GraphBuilderPreviewResult:
    trace_payload = ctx.inputs.to_trace_payload()
    return GraphBuilderPreviewResult(
        step_id="recheck_runtime_scaffold",
        branch_kind=ctx.inputs.decision.branch_kind,
        reason=ctx.inputs.decision.reason,
        trace_payload=trace_payload,
        history_entry=HistoryEntry.branch_selected(
            node=ctx.inputs.current_step_id,
            step_id=ctx.inputs.current_step_id,
            payload=trace_payload,
        ),
    )


@BUILDER.step(node_id="route_finalize_summary")
async def route_finalize_summary(
    ctx,
) -> GraphBuilderPreviewResult:
    trace_payload = ctx.inputs.to_trace_payload()
    return GraphBuilderPreviewResult(
        step_id="finalize_summary",
        branch_kind=ctx.inputs.decision.branch_kind,
        reason=ctx.inputs.decision.reason,
        trace_payload=trace_payload,
        history_entry=HistoryEntry.branch_selected(
            node=ctx.inputs.current_step_id,
            step_id=ctx.inputs.current_step_id,
            payload=trace_payload,
        ),
    )


ROUTE_TRANSITION = (
    BUILDER.decision(
        node_id="route_transition",
        note="Map transition decisions onto host-facing step IDs.",
    )
    .branch(
        BUILDER.match(
            GraphBuilderTransition,
            matches=lambda transition: transition.decision.next_node == "request_missing_access",
        ).to(route_request_missing_access)
    )
    .branch(
        BUILDER.match(
            GraphBuilderTransition,
            matches=lambda transition: transition.decision.next_node == "recheck_runtime_scaffold",
        ).to(route_recheck_runtime_scaffold)
    )
    .branch(
        BUILDER.match(
            GraphBuilderTransition,
            matches=lambda transition: transition.decision.next_node == "finalize_summary",
        ).to(route_finalize_summary)
    )
)


BUILDER.add_edge(BUILDER.start_node, evaluate_transition)
BUILDER.add_edge(evaluate_transition, ROUTE_TRANSITION)
BUILDER.add_edge(route_request_missing_access, BUILDER.end_node)
BUILDER.add_edge(route_recheck_runtime_scaffold, BUILDER.end_node)
BUILDER.add_edge(route_finalize_summary, BUILDER.end_node)


WORKFLOW_GRAPH = BUILDER.build()


START_BUILDER = GraphBuilder(
    name="demo_prompt_loop_graphbuilder_runtime_start",
    state_type=workflow_state.DemoGraphState,
    input_type=GraphBuilderStartInputs,
    output_type=YieldResponse,
    auto_instrument=False,
)


@START_BUILDER.step(node_id="emit_collect_context")
async def emit_collect_context(
    ctx,
) -> YieldResponse:
    node_definition = get_node_definition("collect_context")
    contract = workflow_contract.get_step_contract("collect_context")
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
            "runtime_root_path": str(SKILL_RUNTIME_ROOT),
        },
    )
    return YieldResponse(
        run_id=ctx.inputs.run_id,
        step_id=node_definition.step_id,
        prompt_envelope=prompt_envelope,
    )


START_BUILDER.add_edge(START_BUILDER.start_node, emit_collect_context)
START_BUILDER.add_edge(emit_collect_context, START_BUILDER.end_node)


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


def build_template_context(*, step_id: str, run_state) -> dict:
    del step_id, run_state
    return {
        "runtime_root_path": str(SKILL_RUNTIME_ROOT),
    }


def load_prompt_body(node_key: str, template_context: dict | None = None) -> str:
    return resolve_prompt_asset(
        get_node_definition(node_key).prompt_asset_path,
        template_context=template_context,
    )


def run_transition_preview(
    *,
    state: workflow_state.DemoGraphState,
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
    state: workflow_state.DemoGraphState,
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
