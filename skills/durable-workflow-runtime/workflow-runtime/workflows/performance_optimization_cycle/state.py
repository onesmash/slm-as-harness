from __future__ import annotations

from dataclasses import asdict, dataclass, field

from workflows.common.policies import condition_matches
from workflows.common.repair_payloads import build_default_agent_repair_payload, make_agent_repair_payload


MAIN_STAGE_IDS = ('brainstorm_optimization',
 'research_optimization',
 'plan_optimization',
 'implement_optimization',
 'review_optimization',
 'update_optimization_knowledge_base')
REPAIR_STAGE_IDS = (
    "request_unblocking_input",
    "repair_and_resume",
)


@dataclass
class PerformanceOptimizationCycleWorkflowState:
    attempt_counts: dict[str, int] = field(default_factory=dict)
    workflow_goal: str | None = None
    task_input: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    current_stage_id: str = MAIN_STAGE_IDS[0]
    completed_stages: list[str] = field(default_factory=list)
    return_stage_id: str | None = None
    optimization_hypotheses: list = field(default_factory=list)
    success_criteria: str | None = None
    brainstorm_artifact_path: str | None = None
    research_brief_path: str | None = None
    evidence_summary: str | None = None
    open_risks: list = field(default_factory=list)
    implementation_plan_path: str | None = None
    planned_change_summary: str | None = None
    verification_plan: list = field(default_factory=list)
    implementation_summary: str | None = None
    changed_paths: list = field(default_factory=list)
    submission_test_output: str | None = None
    submission_test_exit_code: object | None = None
    review_summary: str | None = None
    review_findings: list = field(default_factory=list)
    knowledge_base_update_summary: str | None = None
    knowledge_base_artifacts: list = field(default_factory=list)
    artifacts_by_stage: dict[str, list[dict]] = field(default_factory=dict)
    repair_context: dict[str, object] = field(default_factory=dict)


def make_initial_state(request: dict) -> PerformanceOptimizationCycleWorkflowState:
    task_input = dict(request.get("task_input") or {})
    return PerformanceOptimizationCycleWorkflowState(
        workflow_goal=_select_workflow_goal(task_input),
        task_input=task_input,
        context=dict(request.get("context") or {}),
        constraints=dict(request.get("constraints") or {}),
    )


def _select_workflow_goal(task_input: dict) -> str | None:
    for key in ("goal", "objective", "task", "research_goal", "user_prompt"):
        value = task_input.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def serialize_state(state: PerformanceOptimizationCycleWorkflowState) -> dict:
    return asdict(state)


def deserialize_state(payload: dict | None) -> PerformanceOptimizationCycleWorkflowState:
    payload = payload or {}
    return PerformanceOptimizationCycleWorkflowState(
        attempt_counts=dict(payload.get("attempt_counts") or {}),
        workflow_goal=payload.get("workflow_goal"),
        task_input=dict(payload.get("task_input") or {}),
        context=dict(payload.get("context") or {}),
        constraints=dict(payload.get("constraints") or {}),
        current_stage_id=payload.get("current_stage_id") or MAIN_STAGE_IDS[0],
        completed_stages=list(payload.get("completed_stages") or []),
        return_stage_id=payload.get("return_stage_id"),
        optimization_hypotheses=list(payload.get('optimization_hypotheses') or []),
        success_criteria=payload.get('success_criteria'),
        brainstorm_artifact_path=payload.get('brainstorm_artifact_path'),
        research_brief_path=payload.get('research_brief_path'),
        evidence_summary=payload.get('evidence_summary'),
        open_risks=list(payload.get('open_risks') or []),
        implementation_plan_path=payload.get('implementation_plan_path'),
        planned_change_summary=payload.get('planned_change_summary'),
        verification_plan=list(payload.get('verification_plan') or []),
        implementation_summary=payload.get('implementation_summary'),
        changed_paths=list(payload.get('changed_paths') or []),
        submission_test_output=payload.get('submission_test_output'),
        submission_test_exit_code=payload.get('submission_test_exit_code'),
        review_summary=payload.get('review_summary'),
        review_findings=list(payload.get('review_findings') or []),
        knowledge_base_update_summary=payload.get('knowledge_base_update_summary'),
        knowledge_base_artifacts=list(payload.get('knowledge_base_artifacts') or []),
        artifacts_by_stage=dict(payload.get("artifacts_by_stage") or {}),
        repair_context=dict(payload.get("repair_context") or {}),
    )


def record_observation(
    state: PerformanceOptimizationCycleWorkflowState,
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> None:
    state.attempt_counts[current_step_id] = state.attempt_counts.get(current_step_id, 0) + 1
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        state.artifacts_by_stage.setdefault(current_step_id, []).append(structured_output)
        if observation.get("status") == "succeeded":
            if current_step_id == 'brainstorm_optimization':
                state.optimization_hypotheses = _list_value(structured_output.get('optimization_hypotheses'))
                state.success_criteria = structured_output.get('success_criteria')
                state.brainstorm_artifact_path = structured_output.get('brainstorm_artifact_path')
            elif current_step_id == 'research_optimization':
                state.research_brief_path = structured_output.get('research_brief_path')
                state.evidence_summary = structured_output.get('evidence_summary')
                state.open_risks = _list_value(structured_output.get('open_risks'))
            elif current_step_id == 'plan_optimization':
                state.implementation_plan_path = structured_output.get('implementation_plan_path')
                state.planned_change_summary = structured_output.get('planned_change_summary')
                state.verification_plan = _list_value(structured_output.get('verification_plan'))
            elif current_step_id == 'implement_optimization':
                state.implementation_summary = structured_output.get('implementation_summary')
                state.changed_paths = _list_value(structured_output.get('changed_paths'))
                state.submission_test_output = structured_output.get('submission_test_output')
                state.submission_test_exit_code = structured_output.get('submission_test_exit_code')
            elif current_step_id == 'review_optimization':
                state.review_summary = structured_output.get('review_summary')
                state.review_findings = _list_value(structured_output.get('review_findings'))
            elif current_step_id == 'update_optimization_knowledge_base':
                state.knowledge_base_update_summary = structured_output.get('knowledge_base_update_summary')
                state.knowledge_base_artifacts = _list_value(structured_output.get('knowledge_base_artifacts'))
            else:
                pass

    transition_reason = determine_transition_reason(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    if transition_reason is None:
        return
    return_stage_id = determine_return_stage_id(
        current_step_id=current_step_id,
        existing_return_stage_id=state.return_stage_id,
    )
    repair_payload = build_default_agent_repair_payload(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    state.return_stage_id = return_stage_id
    state.repair_context = _build_repair_context(
        current_step_id=current_step_id,
        return_stage_id=return_stage_id,
        transition_reason=transition_reason,
        repair_payload=repair_payload or {},
    )


def determine_return_stage_id(
    *,
    current_step_id: str,
    existing_return_stage_id: str | None,
) -> str | None:
    if current_step_id in REPAIR_STAGE_IDS:
        return existing_return_stage_id
    return current_step_id


def determine_transition_reason(
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> str | None:
    status = observation.get("status")
    if status == "blocked":
        return "blocked"
    if status == "partial":
        return "partial"
    if status == "failed":
        return "failed"
    if verifier_result is not None and not verifier_result.get("passed", False):
        return "verifier_failed"
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        pass
    return None


def apply_transition(state: PerformanceOptimizationCycleWorkflowState, *, current_step_id: str, next_step_id: str) -> None:
    if _is_forward_completion_transition(current_step_id, next_step_id):
        if current_step_id not in state.completed_stages:
            state.completed_stages.append(current_step_id)

    if current_step_id in REPAIR_STAGE_IDS and next_step_id == state.return_stage_id:
        state.return_stage_id = None
        state.repair_context = {}

    state.current_stage_id = next_step_id


def _is_forward_completion_transition(current_step_id: str, next_step_id: str) -> bool:
    if current_step_id not in MAIN_STAGE_IDS:
        return False
    if next_step_id == current_step_id or next_step_id in REPAIR_STAGE_IDS:
        return False
    if next_step_id == 'finalize_optimization_cycle':
        return True
    if next_step_id not in MAIN_STAGE_IDS:
        return False
    return MAIN_STAGE_IDS.index(next_step_id) > MAIN_STAGE_IDS.index(current_step_id)


def _build_repair_context(
    *,
    current_step_id: str,
    return_stage_id: str | None,
    transition_reason: str,
    repair_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "source_stage_id": current_step_id,
        "return_stage_id": return_stage_id or "",
        "transition_reason": transition_reason,
        "repair_payload": dict(repair_payload or {}),
    }


def _list_value(value) -> list:
    return list(value) if isinstance(value, list) else []


def _dict_value(value) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            items.append(text)
    return items
