from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

from workflows.common.policies import condition_matches
from workflows.common.repair_payloads import build_default_agent_repair_payload, make_agent_repair_payload


MAIN_STAGE_IDS = ('warm_start_shared_space',
 'launch_expert_subagents',
 'autonomous_roundtable',
 'reorganize_knowledge_space',
 'synthesize_report',
 'verify_report')
REPAIR_STAGE_IDS = (
    'repair_report',
    "request_unblocking_input",
    "repair_and_resume",
)
DECLARED_RECOVERY_STAGE_IDS = ('repair_report',)
FINAL_STAGE_ID = 'finalize_collaborative_report'
RUNTIME_DEFAULTS = {'max_steps': 24,
 'max_rounds': 8,
 'min_evidence_items': 3,
 'coverage_threshold': 2,
 'max_reorganizations': 3}
MAX_ARTIFACT_JOURNAL_ENTRIES_PER_STAGE = 32
MAX_ARTIFACT_JOURNAL_BYTES = 64 * 1024
MAX_ARTIFACT_PATH_BYTES = 2048
MAX_WORKFLOW_TEXT_BYTES = 16 * 1024
MAX_WORKFLOW_LIST_BYTES = 512 * 1024

_RECOVERY_OUTPUT_SCHEMAS = {'repair_report': {'report_repair_summary': 'string',
                   'repair_actions': 'string[]',
                   'repair_ready': 'boolean'},
 'request_unblocking_input': {'blocking_reason': 'string',
                              'user_action_needed': 'string',
                              'suggested_next_input': 'string?'},
 'repair_and_resume': {'retry_reason': 'string',
                       'retry_notes': 'string',
                       'repair_actions': 'string[]'}}


def recovery_output_validation_error(*, current_step_id: str, structured_output: object) -> str | None:
    schema = _RECOVERY_OUTPUT_SCHEMAS.get(current_step_id)
    if schema is None:
        return None
    if not isinstance(structured_output, dict):
        return "recovery succeeded output must be an object"
    unexpected = sorted(repr(key) for key in structured_output if key not in schema)
    if unexpected:
        return f"{current_step_id} returned unexpected fields: {unexpected}"
    missing = [
        key
        for key, schema_type in schema.items()
        if not schema_type.endswith("?") and key not in structured_output
    ]
    if missing:
        return f"{current_step_id} is missing required fields: {missing}"
    for key, schema_type in schema.items():
        if key not in structured_output:
            continue
        message = _recovery_schema_type_error(
            key,
            structured_output[key],
            schema_type.rstrip("?"),
        )
        if message:
            return message
    if current_step_id == "repair_and_resume":
        actions = structured_output.get("repair_actions")
        if not isinstance(actions, list) or not actions or any(
            not isinstance(item, str) or not item.strip() for item in actions
        ):
            return "repair_actions must contain at least one meaningful action"
    return None


def _recovery_schema_type_error(key: str, value: object, schema_type: str) -> str | None:
    if schema_type == "string":
        if not isinstance(value, str):
            return f"{key} must be a string"
        if not value.strip():
            return f"{key} must be meaningful text"
        return None
    if schema_type == "boolean":
        return None if isinstance(value, bool) else f"{key} must be a boolean"
    if schema_type == "integer":
        return None if isinstance(value, int) and not isinstance(value, bool) else f"{key} must be an integer"
    if schema_type == "number":
        return None if isinstance(value, (int, float)) and not isinstance(value, bool) else f"{key} must be a number"
    if schema_type == "object":
        return None if isinstance(value, dict) else f"{key} must be an object"
    if schema_type.endswith("[]"):
        if not isinstance(value, list):
            return f"{key} must be a list"
        item_type = schema_type[:-2]
        for index, item in enumerate(value):
            message = _recovery_schema_type_error(f"{key}[{index}]", item, item_type)
            if message:
                return message
        return None
    return f"{key} uses unsupported recovery schema type: {schema_type}"


@dataclass
class CoStormAutonomousResearchWorkflowState:
    attempt_counts: dict[str, int] = field(default_factory=dict)
    workflow_goal: str | None = None
    task_input: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    current_stage_id: str = MAIN_STAGE_IDS[0]
    completed_stages: list[str] = field(default_factory=list)
    return_stage_id: str | None = None
    repair_requirements: list = field(default_factory=list)
    repair_evidence: list = field(default_factory=list)
    repair_transition_reason: str | None = None
    repair_blocked_attempts: int = 0
    expert_roster: list = field(default_factory=list)
    conversation_transcript: list = field(default_factory=list)
    knowledge_map_summary: str | None = None
    evidence_registry: list = field(default_factory=list)
    coverage_map: list = field(default_factory=list)
    round_index: int = 0
    expert_round_index: int = 0
    expert_results: list = field(default_factory=list)
    expert_results_complete: bool | None = None
    last_turn_summary: str | None = None
    coverage_assessment: list = field(default_factory=list)
    coverage_decision_rationale: str | None = None
    next_round_validation_plan: list = field(default_factory=list)
    report_scope_status: str | None = None
    round_decision: str | None = None
    coverage_sufficient: bool | None = None
    ready_for_report: bool | None = None
    reorganization_summary: str | None = None
    reorganization_count: int = 0
    outline: str | None = None
    report_path: str | None = None
    report_summary: str | None = None
    report_sections: list = field(default_factory=list)
    quality_verdict: str | None = None
    quality_findings: list = field(default_factory=list)
    citation_coverage_summary: str | None = None
    report_ready: bool | None = None
    verified_report_path: str | None = None
    report_repair_summary: str | None = None
    repair_actions: list = field(default_factory=list)
    unblocking_blocking_reason: str | None = None
    unblocking_user_action_needed: str | None = None
    unblocking_suggested_next_input: str | None = None
    artifacts_by_stage: dict[str, list[dict]] = field(default_factory=dict)
    repair_context: dict[str, object] = field(default_factory=dict)


def make_initial_state(request: dict) -> CoStormAutonomousResearchWorkflowState:
    task_input = dict(request.get("task_input") or {})
    constraints = _normalize_constraints(request.get("constraints") or {})
    return CoStormAutonomousResearchWorkflowState(
        workflow_goal=_select_workflow_goal(task_input),
        task_input=task_input,
        context=dict(request.get("context") or {}),
        constraints=constraints,
    )


def _select_workflow_goal(task_input: dict) -> str | None:
    for key in ("goal", "objective", "task", "research_goal", "user_prompt"):
        value = task_input.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def serialize_state(state: CoStormAutonomousResearchWorkflowState) -> dict:
    raw = asdict(state)
    payload = _compact_value(raw)
    if not isinstance(payload, dict):
        payload = {}
    payload["artifacts_by_stage"] = _normalize_artifact_journal(
        payload.get("artifacts_by_stage")
    )
    # Serialization diagnostics: if a top-level field vanished during compaction,
    # record which one so verifiers and hosts can distinguish a real state loss
    # from a schema mismatch instead of guessing across repair rounds.
    dropped = [key for key in raw if key not in payload]
    if dropped:
        payload["serialization_diagnostics"] = {
            "dropped_fields": dropped,
            "dropped_at": "graph_state_serialize",
            "hint": (
                "fields exceeded graph_state compaction budget "
                f"({MAX_WORKFLOW_LIST_BYTES} bytes); reduce observation payload "
                "size or raise MAX_WORKFLOW_LIST_BYTES"
            ),
        }
    return payload


def _normalize_constraints(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("constraints must be an object")
    normalized = dict(value)
    for key, default in RUNTIME_DEFAULTS.items():
        candidate = normalized.get(key, default)
        if not isinstance(candidate, int) or isinstance(candidate, bool) or candidate <= 0:
            raise ValueError(f"constraints.{key} must be a positive integer")
        normalized[key] = candidate
    return normalized


def _validate_stage_id(value, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    allowed = set(MAIN_STAGE_IDS) | set(REPAIR_STAGE_IDS) | {FINAL_STAGE_ID}
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"invalid persisted current_stage_id: {value!r}")
    return value


def _validate_return_stage_id(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in MAIN_STAGE_IDS:
        raise ValueError(f"invalid persisted return_stage_id: {value!r}")
    return value


def _non_negative_integer(value, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def deserialize_state(payload: dict | None) -> CoStormAutonomousResearchWorkflowState:
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
    workflow_goal = payload.get("workflow_goal")
    if workflow_goal is not None and not isinstance(workflow_goal, str):
        raise ValueError("persisted workflow_goal must be a string or null")
    raw_task_input = payload.get("task_input")
    raw_context = payload.get("context")
    task_input = raw_task_input if raw_task_input is not None else {}
    context = raw_context if raw_context is not None else {}
    if not isinstance(task_input, dict) or not isinstance(context, dict):
        raise ValueError("persisted task_input and context must be objects")
    raw_repair_blocked_attempts = payload.get("repair_blocked_attempts")
    repair_blocked_attempts = (
        raw_repair_blocked_attempts
        if raw_repair_blocked_attempts is not None
        else attempt_counts.get("repair_and_resume", 0)
    )
    current_stage_id = _validate_stage_id(
        payload.get("current_stage_id", MAIN_STAGE_IDS[0])
    )
    return_stage_id = _validate_return_stage_id(payload.get("return_stage_id"))
    raw_completed_stages = payload.get("completed_stages")
    completed_stages = raw_completed_stages if raw_completed_stages is not None else []
    allowed_completed = set(MAIN_STAGE_IDS) | {FINAL_STAGE_ID}
    if not isinstance(completed_stages, list) or any(
        not isinstance(item, str) or item not in allowed_completed
        for item in completed_stages
    ):
        raise ValueError("persisted completed_stages contains an unknown stage")
    return CoStormAutonomousResearchWorkflowState(
        attempt_counts=attempt_counts,
        workflow_goal=workflow_goal,
        task_input=task_input,
        context=context,
        constraints=_normalize_constraints(payload.get("constraints") or {}),
        current_stage_id=current_stage_id,
        completed_stages=completed_stages,
        return_stage_id=return_stage_id,
        repair_requirements=_list_value(payload.get("repair_requirements")),
        repair_evidence=_list_value(payload.get("repair_evidence")),
        repair_transition_reason=_scalar_value(payload.get("repair_transition_reason")),
        repair_blocked_attempts=_non_negative_integer(
            repair_blocked_attempts,
            "persisted repair_blocked_attempts",
        ),
        expert_roster=_list_value(payload.get('expert_roster')),
        conversation_transcript=_list_value(payload.get('conversation_transcript')),
        knowledge_map_summary=_scalar_value(payload.get('knowledge_map_summary')),
        evidence_registry=_list_value(payload.get('evidence_registry')),
        coverage_map=_list_value(payload.get('coverage_map')),
        round_index=_non_negative_integer(payload.get('round_index', 0), 'persisted round_index'),
        expert_round_index=_non_negative_integer(payload.get('expert_round_index', 0), 'persisted expert_round_index'),
        expert_results=_list_value(payload.get('expert_results')),
        expert_results_complete=_scalar_value(payload.get('expert_results_complete')),
        last_turn_summary=_scalar_value(payload.get('last_turn_summary')),
        coverage_assessment=_list_value(payload.get('coverage_assessment')),
        coverage_decision_rationale=_scalar_value(payload.get('coverage_decision_rationale')),
        next_round_validation_plan=_list_value(payload.get('next_round_validation_plan')),
        report_scope_status=_scalar_value(payload.get('report_scope_status')),
        round_decision=_scalar_value(payload.get('round_decision')),
        coverage_sufficient=_scalar_value(payload.get('coverage_sufficient')),
        ready_for_report=_scalar_value(payload.get('ready_for_report')),
        reorganization_summary=_scalar_value(payload.get('reorganization_summary')),
        reorganization_count=_non_negative_integer(payload.get('reorganization_count', 0), 'persisted reorganization_count'),
        outline=_scalar_value(payload.get('outline')),
        report_path=_scalar_value(payload.get('report_path')),
        report_summary=_scalar_value(payload.get('report_summary')),
        report_sections=_list_value(payload.get('report_sections')),
        quality_verdict=_scalar_value(payload.get('quality_verdict')),
        quality_findings=_list_value(payload.get('quality_findings')),
        citation_coverage_summary=_scalar_value(payload.get('citation_coverage_summary')),
        report_ready=_scalar_value(payload.get('report_ready')),
        verified_report_path=_scalar_value(payload.get('verified_report_path')),
        report_repair_summary=_scalar_value(payload.get('report_repair_summary')),
        repair_actions=_list_value(payload.get('repair_actions')),
        unblocking_blocking_reason=_scalar_value(payload.get('unblocking_blocking_reason')),
        unblocking_user_action_needed=_scalar_value(payload.get('unblocking_user_action_needed')),
        unblocking_suggested_next_input=_scalar_value(payload.get('unblocking_suggested_next_input')),
        artifacts_by_stage=_normalize_artifact_journal(payload.get("artifacts_by_stage")),
        repair_context=dict(payload.get("repair_context") or {}),
    )


def _promote_failed_report_stage_output(
    state: CoStormAutonomousResearchWorkflowState,
    *,
    current_step_id: str,
    structured_output: dict,
    verifier_result: dict | None,
) -> None:
    verifier_message = ""
    if isinstance(verifier_result, dict):
        raw_message = verifier_result.get("message")
        if isinstance(raw_message, str) and raw_message.strip():
            verifier_message = raw_message.strip()
    if current_step_id == "synthesize_report":
        if "outline" in structured_output:
            state.outline = _scalar_value(structured_output.get("outline"))
        candidate_path = structured_output.get("report_path")
        if isinstance(candidate_path, str) and candidate_path.strip():
            state.report_path = candidate_path.strip()
        if "report_summary" in structured_output:
            state.report_summary = _scalar_value(structured_output.get("report_summary"))
        if "report_sections" in structured_output:
            state.report_sections = _list_value(structured_output.get("report_sections"))
        return
    if current_step_id != "verify_report":
        return
    findings = _list_value(structured_output.get("quality_findings"))
    failure_message = verifier_message or "verify_report did not complete successfully; repair is required"
    if failure_message not in findings:
        findings = [*findings, failure_message]
    summary = _scalar_value(structured_output.get("citation_coverage_summary"))
    state.quality_verdict = "repair"
    state.quality_findings = findings
    state.citation_coverage_summary = (
        summary if isinstance(summary, str) and summary.strip() else failure_message
    )
    state.report_ready = False
    candidate_path = structured_output.get("verified_report_path")
    if isinstance(candidate_path, str) and candidate_path.strip():
        state.verified_report_path = candidate_path.strip()


def record_observation(
    state: CoStormAutonomousResearchWorkflowState,
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> None:
    state.attempt_counts[current_step_id] = state.attempt_counts.get(current_step_id, 0) + 1
    recovery_output_error = (
        recovery_output_validation_error(
            current_step_id=current_step_id,
            structured_output=observation.get("structured_output"),
        )
        if current_step_id in REPAIR_STAGE_IDS and observation.get("status") == "succeeded"
        else None
    )
    if current_step_id == "repair_and_resume":
        if observation.get("status") == "blocked" or recovery_output_error is not None:
            state.repair_blocked_attempts += 1
        elif observation.get("status") == "succeeded" and recovery_output_error is None:
            state.repair_blocked_attempts = 0
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        verifier_passed = (
            isinstance(verifier_result, dict)
            and verifier_result.get("passed") is True
        )
        if (
            observation.get("status") in {"succeeded", "failed", "blocked", "partial"}
            and current_step_id in {"synthesize_report", "verify_report"}
            and (
                observation.get("status") != "succeeded"
                or not verifier_passed
            )
        ):
            _promote_failed_report_stage_output(
                state,
                current_step_id=current_step_id,
                structured_output=structured_output,
                verifier_result=verifier_result,
            )
        if observation.get("status") == "succeeded" and (
            verifier_passed
            or (current_step_id in REPAIR_STAGE_IDS and recovery_output_error is None)
        ):
            state.artifacts_by_stage.setdefault(current_step_id, []).append(
                _compact_artifact_snapshot(structured_output)
            )
            state.artifacts_by_stage = _normalize_artifact_journal(state.artifacts_by_stage)
            if current_step_id == 'warm_start_shared_space':
                state.expert_roster = _list_value(structured_output.get('expert_roster'))
                state.conversation_transcript = _list_value(structured_output.get('conversation_transcript'))
                state.knowledge_map_summary = _scalar_value(structured_output.get('knowledge_map_summary'))
                state.evidence_registry = _list_value(structured_output.get('evidence_registry'))
                state.coverage_map = _list_value(structured_output.get('coverage_map'))
                state.round_index = _scalar_value(structured_output.get('round_index'))
            elif current_step_id == 'launch_expert_subagents':
                state.expert_round_index = _scalar_value(structured_output.get('expert_round_index'))
                state.expert_results = _list_value(structured_output.get('expert_results'))
                state.expert_results_complete = _scalar_value(structured_output.get('expert_results_complete'))
                state.evidence_registry = _list_value(structured_output.get('evidence_registry'))
            elif current_step_id == 'autonomous_roundtable':
                state.last_turn_summary = _scalar_value(structured_output.get('last_turn_summary'))
                state.conversation_transcript = _list_value(structured_output.get('conversation_transcript'))
                state.evidence_registry = _list_value(structured_output.get('evidence_registry'))
                state.coverage_map = _list_value(structured_output.get('coverage_map'))
                state.coverage_assessment = _list_value(structured_output.get('coverage_assessment'))
                state.coverage_decision_rationale = _scalar_value(structured_output.get('coverage_decision_rationale'))
                state.next_round_validation_plan = _list_value(structured_output.get('next_round_validation_plan'))
                state.report_scope_status = _scalar_value(structured_output.get('report_scope_status'))
                state.knowledge_map_summary = _scalar_value(structured_output.get('knowledge_map_summary'))
                state.expert_roster = _list_value(structured_output.get('expert_roster'))
                state.round_index = _scalar_value(structured_output.get('round_index'))
                state.round_decision = _scalar_value(structured_output.get('round_decision'))
                state.coverage_sufficient = _scalar_value(structured_output.get('coverage_sufficient'))
                state.ready_for_report = _scalar_value(structured_output.get('ready_for_report'))
            elif current_step_id == 'reorganize_knowledge_space':
                state.knowledge_map_summary = _scalar_value(structured_output.get('knowledge_map_summary'))
                state.coverage_map = _list_value(structured_output.get('coverage_map'))
                state.evidence_registry = _list_value(structured_output.get('evidence_registry'))
                state.reorganization_summary = _scalar_value(structured_output.get('reorganization_summary'))
                state.reorganization_count = _scalar_value(structured_output.get('reorganization_count'))
            elif current_step_id == 'synthesize_report':
                state.outline = _scalar_value(structured_output.get('outline'))
                state.report_path = _scalar_value(structured_output.get('report_path'))
                state.report_summary = _scalar_value(structured_output.get('report_summary'))
                state.report_sections = _list_value(structured_output.get('report_sections'))
            elif current_step_id == 'verify_report':
                state.quality_verdict = _scalar_value(structured_output.get('quality_verdict'))
                state.quality_findings = _list_value(structured_output.get('quality_findings'))
                state.citation_coverage_summary = _scalar_value(structured_output.get('citation_coverage_summary'))
                state.report_ready = _scalar_value(structured_output.get('report_ready'))
                state.verified_report_path = _scalar_value(structured_output.get('verified_report_path'))
            elif current_step_id == 'repair_report':
                state.report_repair_summary = _scalar_value(structured_output.get('report_repair_summary'))
                state.repair_actions = _list_value(structured_output.get('repair_actions'))
            elif current_step_id == 'request_unblocking_input':
                state.unblocking_blocking_reason = _scalar_value(structured_output.get('blocking_reason'))
                state.unblocking_user_action_needed = _scalar_value(structured_output.get('user_action_needed'))
                state.unblocking_suggested_next_input = _scalar_value(structured_output.get('suggested_next_input'))
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
        current_step_id=_repair_context_source_stage_id(state, current_step_id),
        return_stage_id=return_stage_id,
        transition_reason=transition_reason,
        repair_payload=repair_payload or {},
    )
    state.repair_context["repair_blocked_attempts"] = state.repair_blocked_attempts


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
    if current_step_id in MAIN_STAGE_IDS and status == "succeeded":
        if not (
            isinstance(verifier_result, dict)
            and verifier_result.get("passed") is True
        ):
            return "verifier_failed"
    if verifier_result is not None and (
        not isinstance(verifier_result, dict)
        or verifier_result.get("passed") is not True
    ):
        return "verifier_failed"
    if current_step_id in REPAIR_STAGE_IDS and status == "succeeded":
        if recovery_output_validation_error(
            current_step_id=current_step_id,
            structured_output=observation.get("structured_output"),
        ) is not None:
            return "verifier_failed"
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        pass
    return None


def apply_transition(state: CoStormAutonomousResearchWorkflowState, *, current_step_id: str, next_step_id: str) -> None:
    if _is_forward_completion_transition(current_step_id, next_step_id):
        if current_step_id not in state.completed_stages:
            state.completed_stages.append(current_step_id)

    if current_step_id in REPAIR_STAGE_IDS and next_step_id == state.return_stage_id:
        state.return_stage_id = None
        state.repair_context = {}
        state.repair_blocked_attempts = 0
    elif (
        current_step_id in DECLARED_RECOVERY_STAGE_IDS
        and next_step_id in MAIN_STAGE_IDS
    ):
        # Clear repair bookkeeping only when the declared recovery stage returns to a
        # main stage. Preserve return_stage_id/repair_context when it is routed onward
        # to a shared repair helper (e.g. repair_report blocked -> repair_and_resume) so
        # the original stage can still be resumed after the helper succeeds.
        state.return_stage_id = None
        state.repair_context = {}

    if current_step_id == "request_unblocking_input" and next_step_id == "repair_and_resume":
        state.repair_blocked_attempts = 0
        state.repair_context["repair_blocked_attempts"] = 0
    elif current_step_id == "repair_and_resume":
        if next_step_id == "request_unblocking_input":
            state.repair_context["repair_blocked_attempts"] = state.repair_blocked_attempts
        elif next_step_id not in REPAIR_STAGE_IDS:
            state.repair_blocked_attempts = 0

    state.current_stage_id = next_step_id


def _is_forward_completion_transition(current_step_id: str, next_step_id: str) -> bool:
    if current_step_id not in MAIN_STAGE_IDS:
        return False
    if next_step_id == current_step_id or next_step_id in REPAIR_STAGE_IDS:
        return False
    if next_step_id == 'finalize_collaborative_report':
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


def _repair_context_source_stage_id(state: CoStormAutonomousResearchWorkflowState, current_step_id: str) -> str:
    if current_step_id != "request_unblocking_input":
        return current_step_id
    existing_context = state.repair_context if isinstance(state.repair_context, dict) else {}
    existing_source = existing_context.get("source_stage_id")
    if existing_source in REPAIR_STAGE_IDS:
        return str(existing_source)
    return current_step_id


def _list_value(value) -> list:
    compact = _compact_value(value)
    return compact if isinstance(compact, list) else []


def _dict_value(value) -> dict:
    compact = _compact_value(value)
    return compact if isinstance(compact, dict) else {}


def _scalar_value(value):
    return _compact_value(value)


def _bounded_text(value: object, *, max_bytes: int = MAX_WORKFLOW_TEXT_BYTES):
    if not isinstance(value, str):
        return value
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    suffix = f"\n...[truncated sha256:{hashlib.sha256(encoded).hexdigest()}]"
    prefix_budget = max(1, max_bytes - len(suffix.encode("utf-8")))
    prefix = encoded[:prefix_budget].decode("utf-8", "ignore")
    return prefix + suffix


def _json_size(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _compact_value(value: object, *, depth: int = 0):
    if depth > 4:
        return None
    if isinstance(value, str):
        return _bounded_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, list):
        compact_list = []
        for item in value:
            compact_list.append(_compact_value(item, depth=depth + 1))
            if _json_size(compact_list) > MAX_WORKFLOW_LIST_BYTES:
                compact_list.pop()
                break
        return compact_list
    if isinstance(value, dict):
        compact_dict = {}
        for key in sorted(value, key=lambda item: str(item)):
            if not isinstance(key, str):
                continue
            compact_dict[key] = _compact_value(value[key], depth=depth + 1)
            if _json_size(compact_dict) > MAX_WORKFLOW_LIST_BYTES:
                # Drop only the oversized field and keep later keys; a hard break
                # here silently discards every subsequent field (including small
                # int fields like round_index) once one large field exceeds the
                # cumulative budget.
                compact_dict.pop(key, None)
                continue
        return compact_dict
    return None


def _compact_artifact_path(value: str) -> str:
    text = value.strip()
    encoded = text.encode("utf-8")
    if len(encoded) <= MAX_ARTIFACT_PATH_BYTES:
        return text
    digest = hashlib.sha256(encoded).hexdigest()
    prefix = encoded[: MAX_ARTIFACT_PATH_BYTES - 80].decode("utf-8", "ignore")
    return f"{prefix}...[sha256:{digest}]"


def _compact_artifact_snapshot(value: dict) -> dict:
    compact = {
        "output_keys": sorted(key for key in value if isinstance(key, str))[:128],
    }
    for key, raw_value in value.items():
        if not isinstance(key, str):
            continue
        if key.endswith("_path") or key.endswith("_paths") or key == "artifact_path":
            if isinstance(raw_value, str):
                compact[key] = _compact_artifact_path(raw_value)
            elif isinstance(raw_value, list):
                compact[key] = [
                    _compact_artifact_path(item)
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
    normalized = {}
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
