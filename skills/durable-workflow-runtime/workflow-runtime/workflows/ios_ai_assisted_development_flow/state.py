from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from workflows.common.policies import max_steps_exceeded_decision as common_max_steps_exceeded_decision
from workflows.common.repair_payloads import build_default_agent_repair_payload


MAX_ARTIFACT_JOURNAL_ENTRIES_PER_STAGE = 32
MAX_ARTIFACT_JOURNAL_BYTES = 64 * 1024


MAIN_STAGE_IDS = ('run_brainstorming',
 'approve_subagent_review',
 'run_spec_review',
 'write_implementation_plan',
 'execute_implementation',
 'run_agentic_release_qa',
 'request_pre_merge_code_review',
 'verify_completion')
REPAIR_STAGE_IDS = (
    "request_unblocking_input",
    "repair_and_resume",
)
FINAL_STAGE_ID = "finalize_delivery_summary"
ALL_STAGE_IDS = set(MAIN_STAGE_IDS) | set(REPAIR_STAGE_IDS) | {FINAL_STAGE_ID}


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
    design_summary: str | None = None
    design_path: str | None = None
    ui_surface_affected: bool | None = None
    visual_spec_detail_summary: str | None = None
    design_comparison_source: str | None = None
    runtime_visual_comparison_scope: str | None = None
    open_questions: list = field(default_factory=list)
    ready_for_subagent_review: bool | None = None
    subagent_review_approved: bool | None = None
    authorization_summary: str | None = None
    ready_for_spec_review: bool | None = None
    spec_review_perspectives: list = field(default_factory=list)
    spec_review_findings_summary: str | None = None
    spec_review_subagent_summaries: list = field(default_factory=list)
    spec_review_artifact_paths: list = field(default_factory=list)
    ready_for_planning: bool | None = None
    plan_summary: str | None = None
    plan_path: str | None = None
    execution_mode: str | None = None
    plan_revision_reason: str | None = None
    ready_for_implementation: bool | None = None
    implementation_summary: str | None = None
    implementation_completed_tasks: list = field(default_factory=list)
    implementation_remaining_tasks: list = field(default_factory=list)
    tasks_completed: bool | None = None
    changed_files: list = field(default_factory=list)
    verification_commands: list = field(default_factory=list)
    open_issues: list = field(default_factory=list)
    debugging_summary: str | None = None
    implementation_verification_passed: bool | None = None
    implementation_plan_updates_required: bool | None = None
    plan_update_summary: str | None = None
    release_qa_verdict: str | None = None
    release_qa_summary: str | None = None
    release_qa_executed_checks: list = field(default_factory=list)
    release_qa_blocked_checks: list = field(default_factory=list)
    release_qa_risk_next_steps: list = field(default_factory=list)
    release_qa_artifacts: list = field(default_factory=list)
    release_qa_target_scope: str | None = None
    review_status: str | None = None
    reviewed_snapshot: str | None = None
    review_findings: list = field(default_factory=list)
    review_summary: str | None = None
    changes_requested: bool | None = None
    completion_verification_passed: bool | None = None
    completion_verification_summary: str | None = None
    completion_verification_evidence: list = field(default_factory=list)
    completion_remaining_risks: list = field(default_factory=list)
    completion_release_qa_risks_resolved: bool | None = None
    completion_release_qa_risk_resolution_summary: str | None = None
    repair_category: str | None = None
    repair_summary: str | None = None
    repair_requirements: list = field(default_factory=list)
    repair_evidence: list = field(default_factory=list)
    repair_transition_reason: str | None = None
    repair_blocked_attempts: int = 0
    unblocking_blocking_reason: str | None = None
    unblocking_user_action_needed: str | None = None
    unblocking_suggested_next_input: str | None = None
    terminal_reason: str | None = None
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
    payload = asdict(state)
    payload["artifacts_by_stage"] = _normalize_artifact_journal(
        state.artifacts_by_stage
    )
    return payload


def deserialize_state(payload: dict | None) -> IosAiAssistedDevelopmentFlowWorkflowState:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("persisted workflow state must be an object")
    raw_task_input = payload.get("task_input")
    raw_context = payload.get("context")
    raw_constraints = payload.get("constraints")
    raw_completed_stages = payload.get("completed_stages")
    if raw_task_input is not None and not isinstance(raw_task_input, dict):
        raise ValueError("persisted task_input must be an object")
    if raw_context is not None and not isinstance(raw_context, dict):
        raise ValueError("persisted context must be an object")
    if raw_constraints is not None and not isinstance(raw_constraints, dict):
        raise ValueError("persisted constraints must be an object")
    if raw_completed_stages is not None and not isinstance(raw_completed_stages, list):
        raise ValueError("persisted completed_stages must be a list")
    completed_stages = list(raw_completed_stages or [])
    if any(
        not isinstance(stage_id, str)
        or stage_id not in set(MAIN_STAGE_IDS) | {FINAL_STAGE_ID}
        for stage_id in completed_stages
    ):
        raise ValueError("persisted completed_stages contains an unknown stage")
    return IosAiAssistedDevelopmentFlowWorkflowState(
        attempt_counts=_normalize_attempt_counts(payload.get("attempt_counts")),
        workflow_goal=payload.get("workflow_goal"),
        task_input=dict(raw_task_input or {}),
        context=dict(raw_context or {}),
        constraints=dict(raw_constraints or {}),
        current_stage_id=_validate_stage_id(payload.get("current_stage_id") or MAIN_STAGE_IDS[0]),
        completed_stages=completed_stages,
        return_stage_id=_validate_return_stage_id(payload.get("return_stage_id")),
        clarification_questions=list(payload.get('clarification_questions') or []),
        clarification_answers_summary=payload.get('clarification_answers_summary'),
        design_summary=payload.get('design_summary'),
        design_path=payload.get('design_path'),
        ui_surface_affected=payload.get('ui_surface_affected'),
        visual_spec_detail_summary=payload.get('visual_spec_detail_summary'),
        design_comparison_source=payload.get('design_comparison_source'),
        runtime_visual_comparison_scope=payload.get('runtime_visual_comparison_scope'),
        open_questions=list(payload.get('open_questions') or []),
        ready_for_subagent_review=payload.get('ready_for_subagent_review'),
        subagent_review_approved=payload.get('subagent_review_approved'),
        authorization_summary=payload.get('authorization_summary'),
        ready_for_spec_review=payload.get('ready_for_spec_review'),
        spec_review_perspectives=list(payload.get('spec_review_perspectives') or []),
        spec_review_findings_summary=payload.get('spec_review_findings_summary'),
        spec_review_subagent_summaries=list(payload.get('spec_review_subagent_summaries') or []),
        spec_review_artifact_paths=list(payload.get('spec_review_artifact_paths') or []),
        ready_for_planning=payload.get('ready_for_planning'),
        plan_summary=payload.get('plan_summary'),
        plan_path=payload.get('plan_path'),
        execution_mode=payload.get('execution_mode'),
        plan_revision_reason=payload.get('plan_revision_reason'),
        ready_for_implementation=payload.get('ready_for_implementation'),
        implementation_summary=payload.get('implementation_summary'),
        implementation_completed_tasks=list(payload.get('implementation_completed_tasks') or []),
        implementation_remaining_tasks=list(payload.get('implementation_remaining_tasks') or []),
        tasks_completed=payload.get('tasks_completed'),
        changed_files=list(payload.get('changed_files') or []),
        verification_commands=list(payload.get('verification_commands') or []),
        open_issues=list(payload.get('open_issues') or []),
        debugging_summary=payload.get('debugging_summary'),
        implementation_verification_passed=payload.get('implementation_verification_passed'),
        implementation_plan_updates_required=payload.get('implementation_plan_updates_required'),
        plan_update_summary=payload.get('plan_update_summary'),
        release_qa_verdict=payload.get('release_qa_verdict'),
        release_qa_summary=payload.get('release_qa_summary'),
        release_qa_executed_checks=list(payload.get('release_qa_executed_checks') or []),
        release_qa_blocked_checks=list(payload.get('release_qa_blocked_checks') or []),
        release_qa_risk_next_steps=list(payload.get('release_qa_risk_next_steps') or []),
        release_qa_artifacts=list(payload.get('release_qa_artifacts') or []),
        release_qa_target_scope=payload.get('release_qa_target_scope'),
        review_status=payload.get('review_status'),
        reviewed_snapshot=payload.get('reviewed_snapshot'),
        review_findings=list(payload.get('review_findings') or []),
        review_summary=payload.get('review_summary'),
        changes_requested=payload.get('changes_requested'),
        completion_verification_passed=payload.get('completion_verification_passed'),
        completion_verification_summary=payload.get('completion_verification_summary'),
        completion_verification_evidence=list(payload.get('completion_verification_evidence') or []),
        completion_remaining_risks=list(payload.get('completion_remaining_risks') or []),
        completion_release_qa_risks_resolved=payload.get('completion_release_qa_risks_resolved'),
        completion_release_qa_risk_resolution_summary=payload.get('completion_release_qa_risk_resolution_summary'),
        repair_category=payload.get('repair_category'),
        repair_summary=payload.get('repair_summary'),
        repair_requirements=list(payload.get('repair_requirements') or []),
        repair_evidence=list(payload.get('repair_evidence') or []),
        repair_transition_reason=payload.get('repair_transition_reason'),
        repair_blocked_attempts=_nonnegative_int(payload.get('repair_blocked_attempts')),
        unblocking_blocking_reason=payload.get('unblocking_blocking_reason'),
        unblocking_user_action_needed=payload.get('unblocking_user_action_needed'),
        unblocking_suggested_next_input=payload.get('unblocking_suggested_next_input'),
        terminal_reason=payload.get('terminal_reason'),
        artifacts_by_stage=_normalize_artifact_journal(payload.get("artifacts_by_stage")),
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
    max_steps_decision = common_max_steps_exceeded_decision(
        current_step_id=current_step_id,
        state=serialize_state(state),
        include_repair_stages=True,
    )
    budget_exhausted = max_steps_decision is not None
    if (
        current_step_id not in REPAIR_STAGE_IDS
        and observation.get("status") == "succeeded"
        and not _verifier_passed(verifier_result)
    ):
        repair_payload = build_default_agent_repair_payload(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if repair_payload is not None:
            return_stage_id = determine_return_stage_id(
                current_step_id=current_step_id,
                existing_return_stage_id=state.return_stage_id,
            )
            state.return_stage_id = return_stage_id
            state.repair_context = _build_repair_context(
                current_step_id=current_step_id,
                return_stage_id=return_stage_id,
                transition_reason="verifier_failed",
                repair_payload=repair_payload,
            )
            _apply_repair_payload(
                state,
                transition_reason="verifier_failed",
                repair_payload=repair_payload,
                reset_blocked_attempts=True,
            )
        if budget_exhausted:
            _mark_max_steps_terminal(state)
        return
    recovery_output_error = recovery_output_validation_error(
        current_step_id=current_step_id,
        structured_output=observation.get("structured_output"),
    ) if current_step_id in REPAIR_STAGE_IDS and observation.get("status") == "succeeded" else None
    if current_step_id == "repair_and_resume":
        if observation.get("status") == "blocked" or recovery_output_error is not None:
            state.repair_blocked_attempts += 1
        elif observation.get("status") == "succeeded":
            state.repair_blocked_attempts = 0
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        verifier_passed = (
            isinstance(verifier_result, dict)
            and verifier_result.get("passed") is True
        )
        if (
            observation.get("status") == "succeeded"
            and (
                verifier_passed
                or (
                    current_step_id in REPAIR_STAGE_IDS
                    and recovery_output_error is None
                )
            )
        ):
            state.artifacts_by_stage.setdefault(current_step_id, []).append(
                _compact_artifact_snapshot(structured_output)
            )
            state.artifacts_by_stage = _normalize_artifact_journal(state.artifacts_by_stage)
            if current_step_id == 'run_brainstorming':
                state.clarification_questions = _list_value(structured_output.get('clarification_questions'))
                state.clarification_answers_summary = structured_output.get('clarification_answers_summary')
                state.design_summary = structured_output.get('design_summary')
                state.design_path = structured_output.get('design_path')
                state.ui_surface_affected = structured_output.get('ui_surface_affected')
                state.visual_spec_detail_summary = structured_output.get('visual_spec_detail_summary')
                state.design_comparison_source = structured_output.get('design_comparison_source')
                state.runtime_visual_comparison_scope = structured_output.get('runtime_visual_comparison_scope')
                state.open_questions = _list_value(structured_output.get('open_questions'))
                state.ready_for_subagent_review = structured_output.get('ready_for_subagent_review')
            elif current_step_id == 'approve_subagent_review':
                state.subagent_review_approved = structured_output.get('subagent_review_approved')
                state.authorization_summary = structured_output.get('authorization_summary')
                state.ready_for_spec_review = structured_output.get('ready_for_spec_review')
            elif current_step_id == 'run_spec_review':
                state.spec_review_perspectives = _list_value(structured_output.get('spec_review_perspectives'))
                state.spec_review_findings_summary = structured_output.get('spec_review_findings_summary')
                state.spec_review_subagent_summaries = _list_value(structured_output.get('spec_review_subagent_summaries'))
                state.spec_review_artifact_paths = _list_value(structured_output.get('spec_review_artifact_paths'))
                state.open_questions = _list_value(structured_output.get('open_questions'))
                state.ready_for_planning = structured_output.get('ready_for_planning')
            elif current_step_id == 'write_implementation_plan':
                state.plan_summary = structured_output.get('plan_summary')
                state.plan_path = structured_output.get('plan_path')
                state.execution_mode = structured_output.get('execution_mode')
                state.open_questions = _list_value(structured_output.get('open_questions'))
                state.plan_revision_reason = structured_output.get('plan_revision_reason')
                state.ready_for_implementation = structured_output.get('ready_for_implementation')
            elif current_step_id == 'execute_implementation':
                state.implementation_summary = structured_output.get('implementation_summary')
                state.implementation_completed_tasks = _list_value(structured_output.get('completed_tasks'))
                state.implementation_remaining_tasks = _list_value(structured_output.get('remaining_tasks'))
                state.tasks_completed = structured_output.get('tasks_completed')
                state.changed_files = _list_value(structured_output.get('changed_files'))
                state.verification_commands = _list_value(structured_output.get('verification_commands'))
                state.open_issues = _list_value(structured_output.get('open_issues'))
                state.debugging_summary = structured_output.get('debugging_summary')
                state.implementation_verification_passed = structured_output.get('verification_passed')
                state.implementation_plan_updates_required = structured_output.get('plan_updates_required')
                state.plan_update_summary = structured_output.get('plan_update_summary')
            elif current_step_id == 'run_agentic_release_qa':
                state.release_qa_verdict = structured_output.get('release_qa_verdict')
                state.release_qa_summary = structured_output.get('release_qa_summary')
                state.release_qa_executed_checks = _list_value(structured_output.get('release_qa_executed_checks'))
                state.release_qa_blocked_checks = _list_value(structured_output.get('release_qa_blocked_checks'))
                state.release_qa_risk_next_steps = _list_value(structured_output.get('release_qa_risk_next_steps'))
                state.release_qa_artifacts = _list_value(structured_output.get('release_qa_artifacts'))
                state.release_qa_target_scope = structured_output.get('release_qa_target_scope')
            elif current_step_id == 'request_pre_merge_code_review':
                state.review_status = structured_output.get('review_status')
                state.reviewed_snapshot = structured_output.get('reviewed_snapshot')
                state.review_findings = _list_value(structured_output.get('findings'))
                state.review_summary = structured_output.get('review_summary')
                state.changes_requested = structured_output.get('changes_requested')
            elif current_step_id == 'verify_completion':
                state.completion_verification_passed = structured_output.get('verification_passed')
                state.completion_verification_summary = structured_output.get('verification_summary')
                state.completion_verification_evidence = _list_value(structured_output.get('verification_evidence'))
                state.completion_remaining_risks = _list_value(structured_output.get('remaining_risks'))
                state.completion_release_qa_risks_resolved = structured_output.get('release_qa_risks_resolved')
                state.completion_release_qa_risk_resolution_summary = structured_output.get('release_qa_risk_resolution_summary')
            elif current_step_id == 'request_unblocking_input':
                blocking_reason = _optional_text(structured_output.get('blocking_reason'))
                user_action_needed = _optional_text(structured_output.get('user_action_needed'))
                suggested_next_input = _optional_text(structured_output.get('suggested_next_input'))
                if blocking_reason is not None:
                    state.unblocking_blocking_reason = blocking_reason
                if user_action_needed is not None:
                    state.unblocking_user_action_needed = user_action_needed
                if suggested_next_input is not None:
                    state.unblocking_suggested_next_input = suggested_next_input
                unblocking_input = {
                    key: value
                    for key, value in {
                        "blocking_reason": blocking_reason,
                        "user_action_needed": user_action_needed,
                        "suggested_next_input": suggested_next_input,
                    }.items()
                    if value is not None
                }
                if unblocking_input:
                    state.repair_context["latest_unblocking_input"] = unblocking_input
            elif current_step_id == 'repair_and_resume':
                _promote_repair_outputs(state, structured_output)
            else:
                pass

    transition_reason = determine_transition_reason(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    if transition_reason is None:
        if budget_exhausted:
            _mark_max_steps_terminal(state)
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
        current_step_id=_repair_context_source_stage_id(state, current_step_id),
        return_stage_id=return_stage_id,
        transition_reason=transition_reason,
        repair_payload=repair_payload or {},
    )
    _apply_repair_payload(
        state,
        transition_reason=transition_reason,
        repair_payload=repair_payload or {},
        reset_blocked_attempts=current_step_id not in REPAIR_STAGE_IDS,
    )
    if budget_exhausted:
        _mark_max_steps_terminal(state)


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
    structured_output = observation.get("structured_output") or {}
    if status == "blocked":
        return "blocked"
    if status == "partial":
        return "partial"
    if status == "failed":
        return "failed"
    if current_step_id in MAIN_STAGE_IDS and status == "succeeded" and not _verifier_passed(verifier_result):
        return "verifier_failed"
    if verifier_result is not None and not _verifier_passed(verifier_result):
        return "verifier_failed"
    if current_step_id in REPAIR_STAGE_IDS and status == "succeeded":
        if recovery_output_validation_error(
            current_step_id=current_step_id,
            structured_output=structured_output,
        ) is not None:
            return "verifier_failed"
    return None


def _compact_artifact_snapshot(value: dict) -> dict:
    compact = {
        "output_keys": sorted(key for key in value if isinstance(key, str))[:128],
    }
    for key, raw_value in value.items():
        if not isinstance(key, str):
            continue
        if key.endswith("_path") or key.endswith("_paths") or key == "artifact_path":
            if isinstance(raw_value, str):
                compact[key] = raw_value[:2048]
            elif isinstance(raw_value, list):
                compact[key] = [
                    item[:2048]
                    for item in raw_value[:128]
                    if isinstance(item, str) and item.strip()
                ]
        elif (
            key.endswith("_index")
            or key.endswith("_count")
            or key.startswith("ready_")
            or key.endswith("_ready")
            or key.endswith("_complete")
            or key.startswith("continue_")
            or key.startswith("should_")
            or key.endswith("_passed")
        ) and isinstance(raw_value, (bool, int)):
            compact[key] = raw_value
    return compact


def _normalize_artifact_journal(value: object) -> dict[str, list[dict]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[dict]] = {}
    for stage_id, entries in value.items():
        if not isinstance(stage_id, str) or not isinstance(entries, list):
            continue
        compact_entries = [
            _compact_artifact_snapshot(item)
            for item in entries[-MAX_ARTIFACT_JOURNAL_ENTRIES_PER_STAGE:]
            if isinstance(item, dict)
        ]
        if compact_entries:
            normalized[stage_id] = compact_entries
    while _json_size(normalized) > MAX_ARTIFACT_JOURNAL_BYTES:
        oldest_stage = next(iter(normalized), None)
        if oldest_stage is None:
            break
        entries = normalized[oldest_stage]
        if len(entries) > 1:
            entries.pop(0)
        else:
            normalized.pop(oldest_stage)
    return normalized


def _json_size(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def apply_transition(state: IosAiAssistedDevelopmentFlowWorkflowState, *, current_step_id: str, next_step_id: str) -> None:
    if _is_forward_completion_transition(current_step_id, next_step_id):
        if current_step_id not in state.completed_stages:
            state.completed_stages.append(current_step_id)
        _clear_repair_state(state)

    if current_step_id == "request_unblocking_input" and next_step_id == "repair_and_resume":
        state.repair_blocked_attempts = 0
        state.repair_context["repair_blocked_attempts"] = 0

    if current_step_id in REPAIR_STAGE_IDS and next_step_id == state.return_stage_id:
        state.return_stage_id = None
        _clear_repair_state(state)

    if current_step_id == "repair_and_resume":
        if next_step_id == "repair_and_resume":
            state.repair_blocked_attempts = max(state.repair_blocked_attempts, 0)
        elif next_step_id == "request_unblocking_input":
            state.repair_context["repair_blocked_attempts"] = state.repair_blocked_attempts
        elif next_step_id not in REPAIR_STAGE_IDS:
            _clear_repair_state(state)

    state.current_stage_id = next_step_id


def max_steps_exceeded_decision(*, current_step_id: str, state: dict):
    return common_max_steps_exceeded_decision(
        current_step_id=current_step_id,
        state=state,
        include_repair_stages=True,
    )


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
    transition_reason: str,
    repair_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "source_stage_id": current_step_id,
        "return_stage_id": return_stage_id or "",
        "transition_reason": transition_reason,
        "repair_category": str(repair_payload.get("category") or ""),
        "repair_summary": str(repair_payload.get("summary") or ""),
        "repair_requirements": _string_list(repair_payload.get("requirements")),
        "repair_evidence": _string_list(repair_payload.get("evidence")),
        "repair_blocked_attempts": 0,
        "repair_payload": dict(repair_payload or {}),
    }


def _repair_context_source_stage_id(
    state: IosAiAssistedDevelopmentFlowWorkflowState,
    current_step_id: str,
) -> str:
    if current_step_id != "request_unblocking_input":
        return current_step_id
    existing_context = state.repair_context if isinstance(state.repair_context, dict) else {}
    existing_source = existing_context.get("source_stage_id")
    if existing_source in REPAIR_STAGE_IDS:
        return str(existing_source)
    return current_step_id


def _apply_repair_payload(
    state: IosAiAssistedDevelopmentFlowWorkflowState,
    *,
    transition_reason: str,
    repair_payload: dict[str, object],
    reset_blocked_attempts: bool,
) -> None:
    state.repair_transition_reason = transition_reason
    state.repair_category = str(repair_payload.get("category") or "")
    state.repair_summary = str(repair_payload.get("summary") or "")
    state.repair_requirements = _string_list(repair_payload.get("requirements"))
    state.repair_evidence = _string_list(repair_payload.get("evidence"))
    if reset_blocked_attempts:
        state.repair_blocked_attempts = 0


def _promote_repair_outputs(
    state: IosAiAssistedDevelopmentFlowWorkflowState,
    structured_output: dict,
) -> None:
    retry_reason = str(structured_output.get("retry_reason") or "").strip()
    retry_notes = str(structured_output.get("retry_notes") or "").strip()
    repair_actions = _string_list(structured_output.get("repair_actions"))

    if retry_reason:
        state.repair_transition_reason = retry_reason
    if retry_notes or retry_reason:
        state.repair_summary = retry_notes or retry_reason
    if repair_actions:
        state.repair_requirements = repair_actions

    state.repair_context.update(
        {
            "latest_retry_reason": retry_reason,
            "latest_retry_notes": retry_notes,
            "latest_repair_actions": repair_actions,
        }
    )
    repair_payload = state.repair_context.get("repair_payload")
    if isinstance(repair_payload, dict):
        if retry_notes or retry_reason:
            repair_payload["summary"] = retry_notes or retry_reason
        if repair_actions:
            repair_payload["requirements"] = repair_actions


def _clear_repair_state(state: IosAiAssistedDevelopmentFlowWorkflowState) -> None:
    state.repair_context = {}
    state.return_stage_id = None
    state.repair_category = None
    state.repair_summary = None
    state.repair_requirements = []
    state.repair_evidence = []
    state.repair_transition_reason = None
    state.repair_blocked_attempts = 0
    state.unblocking_blocking_reason = None
    state.unblocking_user_action_needed = None
    state.unblocking_suggested_next_input = None


def _mark_max_steps_terminal(state: IosAiAssistedDevelopmentFlowWorkflowState) -> None:
    state.terminal_reason = "max_steps_exceeded"
    _clear_repair_state(state)


def _validate_stage_id(value: object) -> str:
    if not isinstance(value, str) or value not in ALL_STAGE_IDS:
        raise ValueError(f"invalid persisted current_stage_id: {value!r}")
    return value


def _validate_return_stage_id(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in MAIN_STAGE_IDS:
        raise ValueError(f"invalid persisted return_stage_id: {value!r}")
    return value


def _verifier_passed(verifier_result: object) -> bool:
    return isinstance(verifier_result, dict) and verifier_result.get("passed") is True


def recovery_output_validation_error(*, current_step_id: str, structured_output: object) -> str | None:
    if not isinstance(structured_output, dict):
        return "recovery succeeded output must be an object"

    if current_step_id == "request_unblocking_input":
        allowed = {"blocking_reason", "user_action_needed", "suggested_next_input"}
        missing = [
            key
            for key in ("blocking_reason", "user_action_needed")
            if _optional_text(structured_output.get(key)) is None
        ]
        if missing:
            return f"request_unblocking_input is missing meaningful fields: {missing}"
        unexpected = sorted(
            repr(key) for key in structured_output if key not in allowed
        )
        if unexpected:
            return f"request_unblocking_input returned unexpected fields: {unexpected}"
        if "suggested_next_input" in structured_output and _optional_text(
            structured_output.get("suggested_next_input")
        ) is None:
            return "suggested_next_input must be meaningful text when provided"
        return None

    if current_step_id == "repair_and_resume":
        allowed = {
            "retry_reason",
            "retry_notes",
            "repair_actions",
            "needs_external_unblocking",
        }
        missing = [
            key
            for key in ("retry_reason", "retry_notes", "repair_actions")
            if key not in structured_output
        ]
        if missing:
            return f"repair_and_resume is missing required fields: {missing}"
        if _optional_text(structured_output.get("retry_reason")) is None:
            return "retry_reason must be meaningful text"
        if _optional_text(structured_output.get("retry_notes")) is None:
            return "retry_notes must be meaningful text"
        actions = structured_output.get("repair_actions")
        if not isinstance(actions, list) or not _string_list(actions):
            return "repair_actions must contain at least one meaningful action"
        if len(_string_list(actions)) != len(actions):
            return "repair_actions must contain only non-empty strings"
        if "needs_external_unblocking" in structured_output and not isinstance(
            structured_output.get("needs_external_unblocking"), bool
        ):
            return "needs_external_unblocking must be boolean when provided"
        unexpected = sorted(
            repr(key) for key in structured_output if key not in allowed
        )
        if unexpected:
            return f"repair_and_resume returned unexpected fields: {unexpected}"
        return None

    return None


def _normalize_attempt_counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, int] = {}
    for key, raw_count in value.items():
        if not isinstance(key, str):
            continue
        count = _nonnegative_int(raw_count)
        if count > 0:
            normalized[key] = count
    return normalized


def _nonnegative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(value, 0)


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


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
