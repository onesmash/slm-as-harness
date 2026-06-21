from __future__ import annotations

from dataclasses import asdict, dataclass, field

from workflows.common.policies import condition_matches


MAIN_STAGE_IDS = ('run_brainstorming',
 'propose_openspec_change',
 'refine_change_with_openspec',
 'approve_refine',
 'execute_implementation',
 'run_agentic_release_qa',
 'request_final_code_review',
 'write_code_kb_feedback')
REPAIR_STAGE_IDS = (
    "request_unblocking_input",
    "repair_and_resume",
)


@dataclass
class IosAiAssistedDevelopmentFlowWorkflowState:
    attempt_counts: dict[str, int] = field(default_factory=dict)
    workflow_goal: str | None = None
    task_input: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    current_stage_id: str = MAIN_STAGE_IDS[0]
    completed_stages: list[str] = field(default_factory=list)
    return_stage_id: str | None = None
    clarification_questions: list = field(default_factory=list)
    clarification_answers_summary: str | None = None
    approved_design_summary: str | None = None
    approved_design_path: str | None = None
    ui_surface_affected: bool | None = None
    spec_review_findings_summary: str | None = None
    open_questions: list = field(default_factory=list)
    change_name: str | None = None
    change_path: str | None = None
    proposal_path: str | None = None
    openspec_design_path: str | None = None
    tasks_path: str | None = None
    spec_paths: list = field(default_factory=list)
    refinement_summary: str | None = None
    changed_artifacts: list = field(default_factory=list)
    refinement_user_approved: bool | None = None
    refinement_user_feedback: str | None = None
    implementation_summary: str | None = None
    changed_files: list = field(default_factory=list)
    verification_commands: list = field(default_factory=list)
    open_issues: list = field(default_factory=list)
    release_qa_verdict: str | None = None
    release_qa_summary: str | None = None
    release_qa_executed_checks: list = field(default_factory=list)
    release_qa_blocked_checks: list = field(default_factory=list)
    release_qa_risk_next_steps: list = field(default_factory=list)
    release_qa_artifacts: list = field(default_factory=list)
    review_status: str | None = None
    reviewed_snapshot: str | None = None
    review_findings: list = field(default_factory=list)
    review_summary: str | None = None
    kb_updated: bool | None = None
    updated_pages: list = field(default_factory=list)
    qa_feedback_path: str | None = None
    kb_checks: list = field(default_factory=list)
    artifacts_by_stage: dict[str, list[dict]] = field(default_factory=dict)
    repair_context: dict[str, object] = field(default_factory=dict)


def make_initial_state(request: dict) -> IosAiAssistedDevelopmentFlowWorkflowState:
    task_input = dict(request.get("task_input") or {})
    return IosAiAssistedDevelopmentFlowWorkflowState(
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


def serialize_state(state: IosAiAssistedDevelopmentFlowWorkflowState) -> dict:
    return asdict(state)


def deserialize_state(payload: dict | None) -> IosAiAssistedDevelopmentFlowWorkflowState:
    payload = payload or {}
    return IosAiAssistedDevelopmentFlowWorkflowState(
        attempt_counts=dict(payload.get("attempt_counts") or {}),
        workflow_goal=payload.get("workflow_goal"),
        task_input=dict(payload.get("task_input") or {}),
        context=dict(payload.get("context") or {}),
        constraints=dict(payload.get("constraints") or {}),
        current_stage_id=payload.get("current_stage_id") or MAIN_STAGE_IDS[0],
        completed_stages=list(payload.get("completed_stages") or []),
        return_stage_id=payload.get("return_stage_id"),
        clarification_questions=list(payload.get('clarification_questions') or []),
        clarification_answers_summary=payload.get('clarification_answers_summary'),
        approved_design_summary=payload.get('approved_design_summary'),
        approved_design_path=payload.get('approved_design_path'),
        ui_surface_affected=payload.get('ui_surface_affected'),
        spec_review_findings_summary=payload.get('spec_review_findings_summary'),
        open_questions=list(payload.get('open_questions') or []),
        change_name=payload.get('change_name'),
        change_path=payload.get('change_path'),
        proposal_path=payload.get('proposal_path'),
        openspec_design_path=payload.get('openspec_design_path'),
        tasks_path=payload.get('tasks_path'),
        spec_paths=list(payload.get('spec_paths') or []),
        refinement_summary=payload.get('refinement_summary'),
        changed_artifacts=list(payload.get('changed_artifacts') or []),
        refinement_user_approved=payload.get('refinement_user_approved'),
        refinement_user_feedback=payload.get('refinement_user_feedback'),
        implementation_summary=payload.get('implementation_summary'),
        changed_files=list(payload.get('changed_files') or []),
        verification_commands=list(payload.get('verification_commands') or []),
        open_issues=list(payload.get('open_issues') or []),
        release_qa_verdict=payload.get('release_qa_verdict'),
        release_qa_summary=payload.get('release_qa_summary'),
        release_qa_executed_checks=list(payload.get('release_qa_executed_checks') or []),
        release_qa_blocked_checks=list(payload.get('release_qa_blocked_checks') or []),
        release_qa_risk_next_steps=list(payload.get('release_qa_risk_next_steps') or []),
        release_qa_artifacts=list(payload.get('release_qa_artifacts') or []),
        review_status=payload.get('review_status'),
        reviewed_snapshot=payload.get('reviewed_snapshot'),
        review_findings=list(payload.get('review_findings') or []),
        review_summary=payload.get('review_summary'),
        kb_updated=payload.get('kb_updated'),
        updated_pages=list(payload.get('updated_pages') or []),
        qa_feedback_path=payload.get('qa_feedback_path'),
        kb_checks=list(payload.get('kb_checks') or []),
        artifacts_by_stage=dict(payload.get("artifacts_by_stage") or {}),
        repair_context=dict(payload.get("repair_context") or {}),
    )


def record_observation(
    state: IosAiAssistedDevelopmentFlowWorkflowState,
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
            if current_step_id == 'run_brainstorming':
                state.clarification_questions = _list_value(structured_output.get('clarification_questions'))
                state.clarification_answers_summary = structured_output.get('clarification_answers_summary')
                state.approved_design_summary = structured_output.get('approved_design_summary')
                state.approved_design_path = structured_output.get('approved_design_path')
                state.ui_surface_affected = structured_output.get('ui_surface_affected')
                state.spec_review_findings_summary = structured_output.get('spec_review_findings_summary')
                state.open_questions = _list_value(structured_output.get('open_questions'))
            elif current_step_id == 'propose_openspec_change':
                state.change_name = structured_output.get('change_name')
                state.change_path = structured_output.get('change_path')
                state.proposal_path = structured_output.get('proposal_path')
                state.openspec_design_path = structured_output.get('openspec_design_path')
                state.tasks_path = structured_output.get('tasks_path')
                state.spec_paths = _list_value(structured_output.get('spec_paths'))
            elif current_step_id == 'refine_change_with_openspec':
                state.refinement_summary = structured_output.get('refinement_summary')
                state.changed_artifacts = _list_value(structured_output.get('changed_artifacts'))
            elif current_step_id == 'approve_refine':
                state.refinement_user_approved = structured_output.get('user_approved')
                state.refinement_user_feedback = structured_output.get('user_feedback')
            elif current_step_id == 'execute_implementation':
                state.implementation_summary = structured_output.get('implementation_summary')
                state.changed_files = _list_value(structured_output.get('changed_files'))
                state.verification_commands = _list_value(structured_output.get('verification_commands'))
                state.open_issues = _list_value(structured_output.get('open_issues'))
            elif current_step_id == 'run_agentic_release_qa':
                state.release_qa_verdict = structured_output.get('release_qa_verdict')
                state.release_qa_summary = structured_output.get('release_qa_summary')
                state.release_qa_executed_checks = _list_value(structured_output.get('release_qa_executed_checks'))
                state.release_qa_blocked_checks = _list_value(structured_output.get('release_qa_blocked_checks'))
                state.release_qa_risk_next_steps = _list_value(structured_output.get('release_qa_risk_next_steps'))
                state.release_qa_artifacts = _list_value(structured_output.get('release_qa_artifacts'))
            elif current_step_id == 'request_final_code_review':
                state.review_status = structured_output.get('review_status')
                state.reviewed_snapshot = structured_output.get('reviewed_snapshot')
                state.review_findings = _list_value(structured_output.get('findings'))
                state.review_summary = structured_output.get('review_summary')
            elif current_step_id == 'write_code_kb_feedback':
                state.kb_updated = structured_output.get('kb_updated')
                state.updated_pages = _list_value(structured_output.get('updated_pages'))
                state.qa_feedback_path = structured_output.get('qa_feedback_path')
                state.kb_checks = _list_value(structured_output.get('kb_checks'))
            else:
                pass

    repair_reason = determine_repair_reason(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    if repair_reason is None:
        return
    return_stage_id = determine_return_stage_id(
        current_step_id=current_step_id,
        existing_return_stage_id=state.return_stage_id,
    )
    state.return_stage_id = return_stage_id
    state.repair_context = _build_repair_context(
        current_step_id=current_step_id,
        return_stage_id=return_stage_id,
        repair_reason=repair_reason,
        observation=observation,
        output=structured_output if isinstance(structured_output, dict) else {},
    )


def determine_return_stage_id(
    *,
    current_step_id: str,
    existing_return_stage_id: str | None,
) -> str | None:
    if current_step_id in MAIN_STAGE_IDS:
        return current_step_id
    if current_step_id in REPAIR_STAGE_IDS:
        return existing_return_stage_id
    return MAIN_STAGE_IDS[0]


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
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        if current_step_id == 'run_agentic_release_qa':
            if condition_matches(structured_output.get('release_qa_verdict'), 'equals', 'blocked'):
                return 'Release QA was blocked and needs missing QA environment, artifact, credential, device, or baseline input.'
        elif current_step_id == 'request_final_code_review':
            if condition_matches(structured_output.get('review_status'), 'equals', 'blocked'):
                return 'Merged-final review reported a blocked status and needs the missing review input.'
        else:
            pass
    return None


def apply_transition(state: IosAiAssistedDevelopmentFlowWorkflowState, *, current_step_id: str, next_step_id: str) -> None:
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
    if next_step_id == "finalize_delivery_summary":
        return True
    if next_step_id not in MAIN_STAGE_IDS:
        return False
    return MAIN_STAGE_IDS.index(next_step_id) > MAIN_STAGE_IDS.index(current_step_id)


def _build_repair_context(
    *,
    current_step_id: str,
    return_stage_id: str | None,
    repair_reason: str,
    observation: dict,
    output: dict,
) -> dict[str, object]:
    details = {
        key: value
        for key, value in output.items()
        if value not in (None, "", [], {})
    }
    error_payload = observation.get("error")
    if isinstance(error_payload, dict) and error_payload:
        details["error"] = dict(error_payload)
    return {
        "source_stage_id": current_step_id,
        "return_stage_id": return_stage_id or "",
        "repair_reason": repair_reason,
        "summary": observation.get("summary", ""),
        "blocked_reason": str(output.get("blocked_reason") or ""),
        "error_message": str(output.get("error_message") or ""),
        "missing_inputs": _string_list(output.get("missing_inputs")),
        "missing_artifacts": _string_list(output.get("missing_artifacts")),
        "failed_commands": _string_list(output.get("failed_commands")),
        "failing_checks": _list_value(output.get("failing_checks")),
        "details": details,
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
