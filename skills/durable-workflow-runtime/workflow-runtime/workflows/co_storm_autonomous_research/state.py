from __future__ import annotations

from dataclasses import asdict, dataclass, field

from workflows.common.policies import condition_matches
from workflows.common.repair_payloads import build_default_agent_repair_payload, make_agent_repair_payload

from .fanout_contract import (
    FanoutContractError,
    build_attempt_snapshot,
    build_canonical_history,
    canonical_history_errors,
    normalize_history,
    parse_binding_records,
    parse_expert_roster,
)


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
MAX_FANOUT_ITEMS = 128
MAX_ATTEMPT_HISTORY = 256
ATTEMPT_SNAPSHOT_FIELDS = frozenset(
    {
        "status",
        "fanout_round_index",
        "expert_ids",
        "subagent_run_ids",
        "artifact_paths",
        "verifier_passed",
    }
)


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
    expert_roster: list = field(default_factory=list)
    conversation_transcript: list = field(default_factory=list)
    knowledge_map_summary: str | None = None
    evidence_registry: list = field(default_factory=list)
    coverage_map: list = field(default_factory=list)
    round_index: object | None = None
    fanout_round_index: object | None = None
    subagent_expert_ids: list = field(default_factory=list)
    subagent_run_ids: list = field(default_factory=list)
    subagent_result_summaries: list = field(default_factory=list)
    subagent_artifact_paths: list = field(default_factory=list)
    subagent_binding_records: list = field(default_factory=list)
    subagent_run_history: list = field(default_factory=list)
    subagent_attempt_history: list = field(default_factory=list)
    current_fanout_attempt: dict = field(default_factory=dict)
    fanout_complete: bool | None = None
    last_turn_summary: str | None = None
    round_decision: str | None = None
    coverage_sufficient: bool | None = None
    ready_for_report: bool | None = None
    reorganization_summary: str | None = None
    reorganization_count: object | None = None
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
    return asdict(state)


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


def _persisted_string_list(payload: dict, key: str, *, unique: bool = True) -> list[str]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"persisted {key} must be a list of non-empty strings")
    normalized = [item.strip() for item in value]
    if unique and len(set(normalized)) != len(normalized):
        raise ValueError(f"persisted {key} must contain unique strings")
    return normalized


def _validate_attempt_snapshot(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"persisted {label} must be an object")
    required = ATTEMPT_SNAPSHOT_FIELDS - {"verifier_passed"}
    if not required.issubset(value) or not set(value).issubset(ATTEMPT_SNAPSHOT_FIELDS):
        raise ValueError(
            f"persisted {label} must contain only the bounded fan-out attempt fields"
        )
    status = value.get("status")
    if not isinstance(status, str) or not status.strip():
        raise ValueError(f"persisted {label}.status must be a non-empty string")
    round_index = value.get("fanout_round_index")
    if round_index is not None and (
        not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 1
    ):
        raise ValueError(f"persisted {label}.fanout_round_index must be a positive integer or null")
    normalized = {
        "status": status.strip(),
        "fanout_round_index": round_index,
    }
    for key in ("expert_ids", "subagent_run_ids", "artifact_paths"):
        raw_values = value.get(key)
        if not isinstance(raw_values, list) or len(raw_values) > MAX_FANOUT_ITEMS:
            raise ValueError(
                f"persisted {label}.{key} must be a bounded list of non-empty strings"
            )
        if any(not isinstance(item, str) or not item.strip() for item in raw_values):
            raise ValueError(
                f"persisted {label}.{key} must contain non-empty strings"
            )
        values = [item.strip() for item in raw_values]
        if len(set(values)) != len(values):
            raise ValueError(f"persisted {label}.{key} must contain unique strings")
        normalized[key] = values
    if "verifier_passed" in value:
        verifier_passed = value["verifier_passed"]
        if not isinstance(verifier_passed, bool):
            raise ValueError(f"persisted {label}.verifier_passed must be boolean")
        normalized["verifier_passed"] = verifier_passed
    return normalized


def _validate_attempt_history(value: object) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_ATTEMPT_HISTORY:
        raise ValueError(
            "persisted subagent_attempt_history must be a bounded list of objects"
        )
    return [
        _validate_attempt_snapshot(item, f"subagent_attempt_history[{index}]")
        for index, item in enumerate(value)
    ]


def deserialize_state(payload: dict | None) -> CoStormAutonomousResearchWorkflowState:
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("persisted workflow state must be an object")
    attempt_counts = dict(payload.get("attempt_counts") or {})
    if any(
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
    task_input = payload.get("task_input")
    context = payload.get("context")
    if task_input is None:
        task_input = {}
    if context is None:
        context = {}
    if not isinstance(task_input, dict) or not isinstance(context, dict):
        raise ValueError("persisted task_input and context must be objects")
    current_stage_id = _validate_stage_id(payload.get("current_stage_id") or MAIN_STAGE_IDS[0])
    return_stage_id = _validate_return_stage_id(payload.get("return_stage_id"))
    completed_stages = list(payload.get("completed_stages") or [])
    allowed_completed = set(MAIN_STAGE_IDS) | {FINAL_STAGE_ID}
    if any(item not in allowed_completed for item in completed_stages):
        raise ValueError("persisted completed_stages contains an unknown stage")
    canonical_history, history_errors = normalize_history(payload.get("subagent_run_history"))
    if history_errors:
        raise ValueError("invalid persisted subagent_run_history: " + "; ".join(history_errors))
    if "expert_roster" in payload and payload.get("expert_roster") is not None:
        persisted_roster = payload.get("expert_roster")
        if persisted_roster == []:
            expert_roster = []
            roster_errors = []
        else:
            expert_roster, roster_errors = parse_expert_roster(persisted_roster)
            if roster_errors:
                raise ValueError("invalid persisted expert_roster: " + "; ".join(roster_errors))
    else:
        expert_roster = []
    history_contract_errors = canonical_history_errors(
        canonical_history,
        [record["id"] for record in expert_roster] or None,
    )
    if history_contract_errors:
        raise ValueError(
            "invalid persisted subagent_run_history: " + "; ".join(history_contract_errors)
        )
    subagent_expert_ids = _persisted_string_list(payload, "subagent_expert_ids")
    subagent_run_ids = _persisted_string_list(payload, "subagent_run_ids")
    subagent_result_summaries = _persisted_string_list(payload, "subagent_result_summaries")
    subagent_artifact_paths = _persisted_string_list(payload, "subagent_artifact_paths")
    if "subagent_binding_records" in payload and payload.get("subagent_binding_records") is not None:
        binding_records, binding_errors = parse_binding_records(payload.get("subagent_binding_records"))
        if binding_errors:
            raise ValueError(
                "invalid persisted subagent_binding_records: " + "; ".join(binding_errors)
            )
    else:
        binding_records = []
    if expert_roster and subagent_expert_ids:
        roster_ids = [record["id"] for record in expert_roster]
        if subagent_expert_ids != roster_ids:
            raise ValueError("persisted subagent_expert_ids must match expert_roster order")
    if (subagent_expert_ids or subagent_run_ids or subagent_result_summaries
            or subagent_artifact_paths or binding_records) and not expert_roster:
        raise ValueError("persisted fan-out records require a structured expert_roster")
    current_fanout_lengths = {
        len(subagent_expert_ids),
        len(subagent_run_ids),
        len(subagent_result_summaries),
        len(subagent_artifact_paths),
        len(binding_records),
    }
    if len(current_fanout_lengths) > 1:
        raise ValueError("persisted fan-out arrays and binding records must have equal lengths")
    if binding_records:
        for index, binding in enumerate(binding_records):
            expected = {
                "expert_id": subagent_expert_ids[index],
                "subagent_run_id": subagent_run_ids[index],
                "summary": subagent_result_summaries[index],
                "artifact_path": subagent_artifact_paths[index],
            }
            if any(binding.get(key) != value for key, value in expected.items()):
                raise ValueError(
                    f"persisted subagent_binding_records[{index}] does not match fan-out arrays"
                )
        spawn_receipts = [binding["spawn_receipt"] for binding in binding_records]
        completion_receipts = [binding["completion_receipt"] for binding in binding_records]
        if len(set(spawn_receipts)) != len(spawn_receipts):
            raise ValueError("persisted spawn receipts must be unique")
        if set(spawn_receipts).intersection(completion_receipts):
            raise ValueError("persisted spawn and completion receipts must not overlap")
    attempt_history = _validate_attempt_history(payload.get("subagent_attempt_history"))
    raw_current_attempt = payload.get("current_fanout_attempt")
    if raw_current_attempt is None or raw_current_attempt == {}:
        current_attempt = {}
    else:
        current_attempt = _validate_attempt_snapshot(
            raw_current_attempt, "current_fanout_attempt"
        )
    round_index = payload.get("round_index")
    if round_index is not None and (
        not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 0
    ):
        raise ValueError("persisted round_index must be a non-negative integer or null")
    fanout_round_index = payload.get("fanout_round_index")
    if fanout_round_index is not None and (
        not isinstance(fanout_round_index, int)
        or isinstance(fanout_round_index, bool)
        or fanout_round_index < 1
    ):
        raise ValueError("persisted fanout_round_index must be a positive integer or null")
    fanout_complete = payload.get("fanout_complete")
    if fanout_complete is not None and not isinstance(fanout_complete, bool):
        raise ValueError("persisted fanout_complete must be boolean or null")
    return CoStormAutonomousResearchWorkflowState(
        attempt_counts=attempt_counts,
        workflow_goal=workflow_goal,
        task_input=task_input,
        context=context,
        constraints=_normalize_constraints(payload.get("constraints") or {}),
        current_stage_id=current_stage_id,
        completed_stages=completed_stages,
        return_stage_id=return_stage_id,
        expert_roster=expert_roster,
        conversation_transcript=list(payload.get('conversation_transcript') or []),
        knowledge_map_summary=payload.get('knowledge_map_summary'),
        evidence_registry=list(payload.get('evidence_registry') or []),
        coverage_map=list(payload.get('coverage_map') or []),
        round_index=round_index,
        fanout_round_index=fanout_round_index,
        subagent_expert_ids=subagent_expert_ids,
        subagent_run_ids=subagent_run_ids,
        subagent_result_summaries=subagent_result_summaries,
        subagent_artifact_paths=subagent_artifact_paths,
        subagent_binding_records=binding_records,
        subagent_run_history=canonical_history,
        subagent_attempt_history=list(attempt_history),
        current_fanout_attempt=dict(current_attempt),
        fanout_complete=fanout_complete,
        last_turn_summary=payload.get('last_turn_summary'),
        round_decision=payload.get('round_decision'),
        coverage_sufficient=payload.get('coverage_sufficient'),
        ready_for_report=payload.get('ready_for_report'),
        reorganization_summary=payload.get('reorganization_summary'),
        reorganization_count=payload.get('reorganization_count'),
        outline=payload.get('outline'),
        report_path=payload.get('report_path'),
        report_summary=payload.get('report_summary'),
        report_sections=list(payload.get('report_sections') or []),
        quality_verdict=payload.get('quality_verdict'),
        quality_findings=list(payload.get('quality_findings') or []),
        citation_coverage_summary=payload.get('citation_coverage_summary'),
        report_ready=payload.get('report_ready'),
        verified_report_path=payload.get('verified_report_path'),
        report_repair_summary=payload.get('report_repair_summary'),
        repair_actions=list(payload.get('repair_actions') or []),
        artifacts_by_stage=dict(payload.get("artifacts_by_stage") or {}),
        repair_context=dict(payload.get("repair_context") or {}),
    )


def record_observation(
    state: CoStormAutonomousResearchWorkflowState,
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> None:
    state.attempt_counts[current_step_id] = state.attempt_counts.get(current_step_id, 0) + 1
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        if current_step_id == "launch_expert_subagents":
            verifier_passed = (
                isinstance(verifier_result, dict)
                and verifier_result.get("passed") is True
            )
        else:
            verifier_passed = verifier_result is None or verifier_result.get("passed") is True
        if current_step_id != "launch_expert_subagents" or (
            observation.get("status") == "succeeded" and verifier_passed
        ):
            state.artifacts_by_stage.setdefault(current_step_id, []).append(structured_output)
        if current_step_id == "launch_expert_subagents":
            state.current_fanout_attempt = build_attempt_snapshot(
                output=structured_output,
                status=observation.get("status"),
                verifier_result=verifier_result,
            )
            state.subagent_attempt_history.append(dict(state.current_fanout_attempt))
        if observation.get("status") == "succeeded" and verifier_passed:
            if current_step_id == 'warm_start_shared_space':
                state.expert_roster = _list_value(structured_output.get('expert_roster'))
                state.conversation_transcript = _list_value(structured_output.get('conversation_transcript'))
                state.knowledge_map_summary = structured_output.get('knowledge_map_summary')
                state.evidence_registry = _list_value(structured_output.get('evidence_registry'))
                state.coverage_map = _list_value(structured_output.get('coverage_map'))
                state.round_index = structured_output.get('round_index')
            elif current_step_id == 'launch_expert_subagents':
                state.fanout_round_index = structured_output.get('fanout_round_index')
                state.subagent_expert_ids = _list_value(structured_output.get('subagent_expert_ids'))
                state.subagent_run_ids = _list_value(structured_output.get('subagent_run_ids'))
                state.subagent_result_summaries = _list_value(structured_output.get('subagent_result_summaries'))
                state.subagent_artifact_paths = _list_value(structured_output.get('subagent_artifact_paths'))
                state.subagent_binding_records = _list_value(structured_output.get('subagent_binding_records'))
                try:
                    state.subagent_run_history = build_canonical_history(
                        previous_history=state.subagent_run_history,
                        round_index=structured_output.get('fanout_round_index'),
                        expert_ids=structured_output.get('subagent_expert_ids'),
                        run_ids=structured_output.get('subagent_run_ids'),
                        artifact_paths=structured_output.get('subagent_artifact_paths'),
                    )
                except FanoutContractError as exc:
                    raise ValueError(f"cannot promote fan-out canonical history: {exc}") from exc
                state.current_fanout_attempt = {}
                state.fanout_complete = structured_output.get('fanout_complete')
            elif current_step_id == 'autonomous_roundtable':
                state.last_turn_summary = structured_output.get('last_turn_summary')
                state.conversation_transcript = _list_value(structured_output.get('conversation_transcript'))
                state.evidence_registry = _list_value(structured_output.get('evidence_registry'))
                state.coverage_map = _list_value(structured_output.get('coverage_map'))
                state.knowledge_map_summary = structured_output.get('knowledge_map_summary')
                state.expert_roster = _list_value(structured_output.get('expert_roster'))
                state.round_index = structured_output.get('round_index')
                state.round_decision = structured_output.get('round_decision')
                state.coverage_sufficient = structured_output.get('coverage_sufficient')
                state.ready_for_report = structured_output.get('ready_for_report')
            elif current_step_id == 'reorganize_knowledge_space':
                state.knowledge_map_summary = structured_output.get('knowledge_map_summary')
                state.coverage_map = _list_value(structured_output.get('coverage_map'))
                state.evidence_registry = _list_value(structured_output.get('evidence_registry'))
                state.reorganization_summary = structured_output.get('reorganization_summary')
                state.reorganization_count = structured_output.get('reorganization_count')
            elif current_step_id == 'synthesize_report':
                state.outline = structured_output.get('outline')
                state.report_path = structured_output.get('report_path')
                state.report_summary = structured_output.get('report_summary')
                state.report_sections = _list_value(structured_output.get('report_sections'))
            elif current_step_id == 'verify_report':
                state.quality_verdict = structured_output.get('quality_verdict')
                state.quality_findings = _list_value(structured_output.get('quality_findings'))
                state.citation_coverage_summary = structured_output.get('citation_coverage_summary')
                state.report_ready = structured_output.get('report_ready')
                state.verified_report_path = structured_output.get('verified_report_path')
            elif current_step_id == 'repair_report':
                state.report_repair_summary = structured_output.get('report_repair_summary')
                state.repair_actions = _list_value(structured_output.get('repair_actions'))
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
    if (
        current_step_id == "launch_expert_subagents"
        and status == "succeeded"
        and not (isinstance(verifier_result, dict) and verifier_result.get("passed") is True)
    ):
        return "verifier_failed"
    if verifier_result is not None and not verifier_result.get("passed", False):
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
    elif current_step_id in DECLARED_RECOVERY_STAGE_IDS and next_step_id != current_step_id:
        state.return_stage_id = None
        state.repair_context = {}

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
