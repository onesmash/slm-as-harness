from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from workflows.common.policies import condition_matches
from workflows.common.repair_payloads import build_default_agent_repair_payload, make_agent_repair_payload


MAX_ARTIFACT_JOURNAL_ENTRIES_PER_STAGE = 32
MAX_ARTIFACT_JOURNAL_BYTES = 64 * 1024


MAIN_STAGE_IDS = ('diagnose_performance',
 'brainstorm_optimization',
 'research_optimization',
 'implement_optimization',
 'review_optimization',
 'update_optimization_knowledge_base')
REPAIR_STAGE_IDS = (
    'capture_blocked_cycle_knowledge',
    "request_unblocking_input",
    "repair_and_resume",
)
DECLARED_RECOVERY_STAGE_IDS = ('capture_blocked_cycle_knowledge',)
DEFAULT_MAX_CYCLES = 3
FINAL_STAGE_ID = "finalize_optimization_cycle"


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
    baseline_metrics: str | None = None
    bottleneck_summary: str | None = None
    performance_report_path: str | None = None
    optimization_hypotheses: list = field(default_factory=list)
    success_criteria: str | None = None
    brainstorm_artifact_path: str | None = None
    research_brief_path: str | None = None
    evidence_summary: str | None = None
    open_risks: list = field(default_factory=list)
    planned_change_summary: str | None = None
    verification_plan: list = field(default_factory=list)
    implementation_summary: str | None = None
    changed_paths: list = field(default_factory=list)
    submission_test_output: str | None = None
    submission_test_exit_code: object | None = None
    submission_test_command: str | None = None
    submission_tests_passed: object | None = None
    ready_for_review: object | None = None
    review_summary: str | None = None
    review_findings: list = field(default_factory=list)
    knowledge_base_update_summary: str | None = None
    knowledge_base_artifacts: list = field(default_factory=list)
    continue_optimization: bool | None = None
    completed_optimization_cycles: int = 0
    blocked_cycle_next_lead: str | None = None
    artifacts_by_stage: dict[str, list[dict]] = field(default_factory=dict)
    repair_context: dict[str, object] = field(default_factory=dict)


def make_initial_state(request: dict) -> PerformanceOptimizationCycleWorkflowState:
    task_input = dict(request.get("task_input") or {})
    return PerformanceOptimizationCycleWorkflowState(
        workflow_goal=_select_workflow_goal(task_input),
        task_input=task_input,
        context=dict(request.get("context") or {}),
        constraints=_normalize_constraints(request.get("constraints") or {}),
    )


def _select_workflow_goal(task_input: dict) -> str | None:
    for key in ("goal", "objective", "task", "research_goal", "user_prompt"):
        value = task_input.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_constraints(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("constraints must be an object")
    normalized = dict(value)
    max_cycles = normalized.get("max_cycles", DEFAULT_MAX_CYCLES)
    if not isinstance(max_cycles, int) or isinstance(max_cycles, bool) or max_cycles <= 0:
        raise ValueError("constraints.max_cycles must be a positive integer")
    normalized["max_cycles"] = max_cycles
    return normalized


def serialize_state(state: PerformanceOptimizationCycleWorkflowState) -> dict:
    payload = asdict(state)
    payload["artifacts_by_stage"] = _normalize_artifact_journal(
        state.artifacts_by_stage
    )
    return payload


def deserialize_state(payload: dict | None) -> PerformanceOptimizationCycleWorkflowState:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("persisted workflow state must be an object")
    raw_attempt_counts = payload.get("attempt_counts")
    attempt_counts = raw_attempt_counts if raw_attempt_counts is not None else {}
    if not isinstance(attempt_counts, dict) or any(
        not isinstance(key, str)
        or not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for key, value in attempt_counts.items()
    ):
        raise ValueError("persisted attempt_counts must contain non-negative integer values")
    raw_task_input = payload.get("task_input")
    raw_context = payload.get("context")
    task_input = raw_task_input if raw_task_input is not None else {}
    context = raw_context if raw_context is not None else {}
    if not isinstance(task_input, dict) or not isinstance(context, dict):
        raise ValueError("persisted task_input and context must be objects")
    raw_completed_stages = payload.get("completed_stages")
    completed_stages = raw_completed_stages if raw_completed_stages is not None else []
    if not isinstance(completed_stages, list):
        raise ValueError("persisted completed_stages must be a list")
    allowed_completed = set(MAIN_STAGE_IDS) | {FINAL_STAGE_ID}
    if any(
        not isinstance(item, str) or item not in allowed_completed
        for item in completed_stages
    ):
        raise ValueError("persisted completed_stages contains an unknown stage")
    current_stage_id = _validate_stage_id(
        payload.get("current_stage_id", MAIN_STAGE_IDS[0])
    )
    return_stage_id = _validate_return_stage_id(payload.get("return_stage_id"))
    return PerformanceOptimizationCycleWorkflowState(
        attempt_counts=attempt_counts,
        workflow_goal=payload.get("workflow_goal"),
        task_input=task_input,
        context=context,
        constraints=_normalize_constraints(payload.get("constraints") or {}),
        current_stage_id=current_stage_id,
        completed_stages=completed_stages,
        return_stage_id=return_stage_id,
        baseline_metrics=payload.get('baseline_metrics'),
        bottleneck_summary=payload.get('bottleneck_summary'),
        performance_report_path=payload.get('performance_report_path'),
        optimization_hypotheses=list(payload.get('optimization_hypotheses') or []),
        success_criteria=payload.get('success_criteria'),
        brainstorm_artifact_path=payload.get('brainstorm_artifact_path'),
        research_brief_path=payload.get('research_brief_path'),
        evidence_summary=payload.get('evidence_summary'),
        open_risks=list(payload.get('open_risks') or []),
        planned_change_summary=payload.get('planned_change_summary'),
        verification_plan=list(payload.get('verification_plan') or []),
        implementation_summary=payload.get('implementation_summary'),
        changed_paths=list(payload.get('changed_paths') or []),
        submission_test_output=payload.get('submission_test_output'),
        submission_test_exit_code=payload.get('submission_test_exit_code'),
        submission_test_command=payload.get('submission_test_command'),
        submission_tests_passed=payload.get('submission_tests_passed'),
        ready_for_review=payload.get('ready_for_review'),
        review_summary=payload.get('review_summary'),
        review_findings=list(payload.get('review_findings') or []),
        knowledge_base_update_summary=payload.get('knowledge_base_update_summary'),
        knowledge_base_artifacts=list(payload.get('knowledge_base_artifacts') or []),
        continue_optimization=payload.get('continue_optimization'),
        completed_optimization_cycles=_non_negative_integer(
            payload.get("completed_optimization_cycles", 0),
            "persisted completed_optimization_cycles",
        ),
        blocked_cycle_next_lead=payload.get('blocked_cycle_next_lead'),
        artifacts_by_stage=dict(payload.get("artifacts_by_stage") or {}),
        repair_context=dict(payload.get("repair_context") or {}),
    )


def _validate_stage_id(value: object) -> str:
    allowed = set(MAIN_STAGE_IDS) | set(REPAIR_STAGE_IDS) | {FINAL_STAGE_ID}
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"invalid persisted current_stage_id: {value!r}")
    return value


def _validate_return_stage_id(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in MAIN_STAGE_IDS:
        raise ValueError(f"invalid persisted return_stage_id: {value!r}")
    return value


def record_observation(
    state: PerformanceOptimizationCycleWorkflowState,
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> None:
    state.attempt_counts[current_step_id] = state.attempt_counts.get(current_step_id, 0) + 1
    if (
        current_step_id == "update_optimization_knowledge_base"
        and observation.get("status") == "succeeded"
        and isinstance(verifier_result, dict)
        and verifier_result.get("passed") is True
    ):
        state.completed_optimization_cycles += 1
    structured_output = observation.get("structured_output") or {}
    verifier_passed = (
        isinstance(verifier_result, dict)
        and verifier_result.get("passed") is True
    )
    if isinstance(structured_output, dict) and observation.get("status") == "succeeded" and verifier_passed:
        state.artifacts_by_stage.setdefault(current_step_id, []).append(
            _compact_artifact_snapshot(structured_output)
        )
        state.artifacts_by_stage = _normalize_artifact_journal(state.artifacts_by_stage)
        if current_step_id == 'diagnose_performance':
            state.baseline_metrics = structured_output.get('baseline_metrics')
            state.bottleneck_summary = structured_output.get('bottleneck_summary')
            state.performance_report_path = structured_output.get('performance_report_path')
        elif current_step_id == 'brainstorm_optimization':
            state.optimization_hypotheses = _list_value(structured_output.get('optimization_hypotheses'))
            state.success_criteria = structured_output.get('success_criteria')
            state.brainstorm_artifact_path = structured_output.get('brainstorm_artifact_path')
        elif current_step_id == 'research_optimization':
            state.research_brief_path = structured_output.get('research_brief_path')
            state.evidence_summary = structured_output.get('evidence_summary')
            state.open_risks = _list_value(structured_output.get('open_risks'))
            state.planned_change_summary = structured_output.get('planned_change_summary')
            state.verification_plan = _list_value(structured_output.get('verification_plan'))
        elif current_step_id == 'implement_optimization':
            state.implementation_summary = structured_output.get('implementation_summary')
            state.planned_change_summary = structured_output.get('planned_change_summary')
            state.verification_plan = _list_value(structured_output.get('verification_plan'))
            state.changed_paths = _list_value(structured_output.get('changed_paths'))
            state.submission_test_output = structured_output.get('submission_test_output')
            state.submission_test_exit_code = structured_output.get('submission_test_exit_code')
            state.submission_test_command = structured_output.get('submission_test_command')
            state.submission_tests_passed = structured_output.get('submission_tests_passed')
            state.ready_for_review = structured_output.get('ready_for_review')
        elif current_step_id == 'review_optimization':
            state.review_summary = structured_output.get('review_summary')
            state.review_findings = _list_value(structured_output.get('review_findings'))
        elif current_step_id == 'update_optimization_knowledge_base':
            state.knowledge_base_update_summary = structured_output.get('knowledge_base_update_summary')
            state.knowledge_base_artifacts = _list_value(structured_output.get('knowledge_base_artifacts'))
            state.continue_optimization = structured_output.get('continue_optimization')
        elif current_step_id == 'capture_blocked_cycle_knowledge':
            state.knowledge_base_update_summary = structured_output.get('knowledge_base_update_summary')
            state.knowledge_base_artifacts = _list_value(structured_output.get('knowledge_base_artifacts'))
            state.blocked_cycle_next_lead = structured_output.get('next_cycle_lead')

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


def _non_negative_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


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
    if verifier_result is not None and (
        not isinstance(verifier_result, dict)
        or verifier_result.get("passed") is not True
    ):
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
    elif current_step_id in DECLARED_RECOVERY_STAGE_IDS and next_step_id != current_step_id:
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
