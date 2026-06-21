from __future__ import annotations

from dataclasses import asdict, dataclass, field


MAIN_STAGE_IDS = ("run_primary_stage",)
REPAIR_STAGE_IDS = (
    "request_unblocking_input",
    "repair_and_resume",
)


@dataclass
class ExampleWorkflowState:
    attempt_counts: dict[str, int] = field(default_factory=dict)
    workflow_goal: str | None = None
    current_stage_id: str = "run_primary_stage"
    completed_stages: list[str] = field(default_factory=list)
    return_stage_id: str | None = None
    artifacts_by_stage: dict[str, list[dict]] = field(default_factory=dict)
    repair_context: dict[str, object] = field(default_factory=dict)


def make_initial_state(request: dict) -> ExampleWorkflowState:
    task_input = request.get("task_input") or {}
    return ExampleWorkflowState(
        workflow_goal=task_input.get("goal"),
    )


def serialize_state(state: ExampleWorkflowState) -> dict:
    return asdict(state)


def deserialize_state(payload: dict | None) -> ExampleWorkflowState:
    payload = payload or {}
    return ExampleWorkflowState(
        attempt_counts=dict(payload.get("attempt_counts") or {}),
        workflow_goal=payload.get("workflow_goal"),
        current_stage_id=payload.get("current_stage_id") or "run_primary_stage",
        completed_stages=list(payload.get("completed_stages") or []),
        return_stage_id=payload.get("return_stage_id"),
        artifacts_by_stage=dict(payload.get("artifacts_by_stage") or {}),
        repair_context=dict(payload.get("repair_context") or {}),
    )


def record_observation(
    state: ExampleWorkflowState,
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> None:
    state.attempt_counts[current_step_id] = state.attempt_counts.get(current_step_id, 0) + 1
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        state.artifacts_by_stage.setdefault(current_step_id, []).append(structured_output)

    repair_reason = determine_repair_reason(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    if repair_reason is None:
        return
    return_stage_id = determine_return_stage_id(current_step_id=current_step_id)
    state.return_stage_id = return_stage_id
    state.repair_context = {
        "source_stage_id": current_step_id,
        "return_stage_id": return_stage_id,
        "repair_reason": repair_reason,
        "summary": observation.get("summary", ""),
    }


def determine_return_stage_id(*, current_step_id: str) -> str:
    return current_step_id


def determine_repair_reason(
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> str | None:
    status = observation.get("status")
    if status == "blocked":
        return f"{current_step_id} is blocked and needs external input"
    if status == "partial":
        return f"{current_step_id} only partially completed"
    if status == "failed":
        return f"{current_step_id} failed and needs another attempt"
    if verifier_result is not None and not verifier_result.get("passed", False):
        return f"{current_step_id} did not satisfy verifier checks"
    return None


def apply_transition(state: ExampleWorkflowState, *, current_step_id: str, next_step_id: str) -> None:
    if current_step_id in MAIN_STAGE_IDS and next_step_id not in REPAIR_STAGE_IDS and next_step_id != current_step_id:
        if current_step_id not in state.completed_stages:
            state.completed_stages.append(current_step_id)

    if current_step_id in REPAIR_STAGE_IDS and next_step_id == state.return_stage_id:
        state.return_stage_id = None
        state.repair_context = {}

    state.current_stage_id = next_step_id
