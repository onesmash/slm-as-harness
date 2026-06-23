from __future__ import annotations

from dataclasses import asdict, dataclass, field

from workflows.common.repair_payloads import (
    build_default_agent_repair_payload,
    make_agent_repair_payload,
)


MAIN_STAGE_IDS = (
    "collect_research_context",
    "plan_academic_pipeline",
    "run_research_stage",
    "run_write_stage",
    "run_pre_review_integrity",
    "run_review_stage",
    "run_revision_stage",
    "run_rereview_stage",
    "run_final_integrity",
    "finalize_publication_package",
    "generate_process_summary",
)
REPAIR_STAGE_IDS = (
    "request_unblocking_input",
    "repair_and_resume",
)


@dataclass
class AcademicResearchPipelineState:
    attempt_counts: dict[str, int] = field(default_factory=dict)
    research_goal: str | None = None
    entry_stage: str | None = None
    current_stage_id: str = "collect_research_context"
    completed_stages: list[str] = field(default_factory=list)
    return_stage_id: str | None = None
    next_stage: str | None = None
    stage_plan: list[dict] = field(default_factory=list)
    mode_selection: dict[str, object] = field(default_factory=dict)
    available_materials: list[dict] = field(default_factory=list)
    paper_path: str | None = None
    draft_path: str | None = None
    material_passport_path: str | None = None
    research_artifact_paths: list[str] = field(default_factory=list)
    review_package_path: str | None = None
    revision_roadmap_path: str | None = None
    revised_draft_path: str | None = None
    rereview_package_path: str | None = None
    final_integrity_report_path: str | None = None
    output_package_paths: list[str] = field(default_factory=list)
    process_summary_path: str | None = None
    editorial_decision: str | None = None
    rereview_decision: str | None = None
    integrity_passed: bool | None = None
    final_integrity_passed: bool | None = None
    revision_loop_count: int = 0
    artifacts_by_stage: dict[str, list[dict]] = field(default_factory=dict)
    repair_context: dict[str, object] = field(default_factory=dict)
    output_dir: str | None = None
    source_materials_path: str | None = None
    require_user_checkpoints: bool = True
    enable_claim_audit: bool = False
    allow_format_render: bool = True
    max_revision_loops: int = 2


def make_initial_state(request: dict) -> AcademicResearchPipelineState:
    task_input = request.get("task_input") or {}
    context = request.get("context") or {}
    constraints = request.get("constraints") or {}
    return AcademicResearchPipelineState(
        research_goal=task_input.get("research_goal") or task_input.get("goal"),
        entry_stage=task_input.get("entry_stage"),
        paper_path=context.get("paper_path"),
        material_passport_path=context.get("material_passport_path"),
        output_dir=context.get("output_dir"),
        source_materials_path=context.get("source_materials_path"),
        require_user_checkpoints=constraints.get("require_user_checkpoints", True) is not False,
        enable_claim_audit=constraints.get("enable_claim_audit") is True,
        allow_format_render=constraints.get("allow_format_render", True) is not False,
        max_revision_loops=_positive_int(constraints.get("max_revision_loops"), default=2),
    )


def serialize_state(state: AcademicResearchPipelineState) -> dict:
    return asdict(state)


def deserialize_state(payload: dict | None) -> AcademicResearchPipelineState:
    payload = payload or {}
    return AcademicResearchPipelineState(
        attempt_counts=dict(payload.get("attempt_counts") or {}),
        research_goal=payload.get("research_goal"),
        entry_stage=payload.get("entry_stage"),
        current_stage_id=payload.get("current_stage_id") or "collect_research_context",
        completed_stages=list(payload.get("completed_stages") or []),
        return_stage_id=payload.get("return_stage_id"),
        next_stage=payload.get("next_stage"),
        stage_plan=list(payload.get("stage_plan") or []),
        mode_selection=dict(payload.get("mode_selection") or {}),
        available_materials=list(payload.get("available_materials") or []),
        paper_path=payload.get("paper_path"),
        draft_path=payload.get("draft_path"),
        material_passport_path=payload.get("material_passport_path"),
        research_artifact_paths=list(payload.get("research_artifact_paths") or []),
        review_package_path=payload.get("review_package_path"),
        revision_roadmap_path=payload.get("revision_roadmap_path"),
        revised_draft_path=payload.get("revised_draft_path"),
        rereview_package_path=payload.get("rereview_package_path"),
        final_integrity_report_path=payload.get("final_integrity_report_path"),
        output_package_paths=list(payload.get("output_package_paths") or []),
        process_summary_path=payload.get("process_summary_path"),
        editorial_decision=payload.get("editorial_decision"),
        rereview_decision=payload.get("rereview_decision"),
        integrity_passed=payload.get("integrity_passed"),
        final_integrity_passed=payload.get("final_integrity_passed"),
        revision_loop_count=_positive_int(payload.get("revision_loop_count"), default=0),
        artifacts_by_stage=dict(payload.get("artifacts_by_stage") or {}),
        repair_context=dict(payload.get("repair_context") or {}),
        output_dir=payload.get("output_dir"),
        source_materials_path=payload.get("source_materials_path"),
        require_user_checkpoints=payload.get("require_user_checkpoints", True) is not False,
        enable_claim_audit=payload.get("enable_claim_audit") is True,
        allow_format_render=payload.get("allow_format_render", True) is not False,
        max_revision_loops=_positive_int(payload.get("max_revision_loops"), default=2),
    )


def record_observation(
    state: AcademicResearchPipelineState,
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> None:
    state.attempt_counts[current_step_id] = state.attempt_counts.get(current_step_id, 0) + 1
    structured_output = observation.get("structured_output") or {}
    if isinstance(structured_output, dict):
        state.artifacts_by_stage.setdefault(current_step_id, []).append(structured_output)

    if observation.get("status") == "succeeded" and isinstance(structured_output, dict):
        _record_success_payload(state, current_step_id=current_step_id, output=structured_output)

    transition_reason = determine_transition_reason(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    if transition_reason is None:
        return
    return_stage_id = determine_return_stage_id(current_step_id=current_step_id, observation=observation)
    repair_payload = _build_agent_repair_payload(
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


def determine_return_stage_id(*, current_step_id: str, observation: dict) -> str:
    output = observation.get("structured_output") or {}
    if current_step_id == "run_review_stage":
        decision = _normalize_decision(output.get("editorial_decision"))
        if decision == "reject":
            return "run_research_stage"
        if decision in {"minor_revision", "major_revision"}:
            return "run_revision_stage"
    if current_step_id == "run_rereview_stage":
        if output.get("ready_for_final_integrity") is False:
            return "run_revision_stage"
    if current_step_id in {"run_pre_review_integrity", "run_final_integrity"}:
        return current_step_id
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
    output = observation.get("structured_output") or {}
    if not isinstance(output, dict):
        return None
    if current_step_id == "run_pre_review_integrity" and output.get("integrity_passed") is False:
        return "business_rule_failed"
    if current_step_id == "run_final_integrity" and output.get("final_integrity_passed") is False:
        return "business_rule_failed"
    return None


def apply_transition(state: AcademicResearchPipelineState, *, current_step_id: str, next_step_id: str) -> None:
    if current_step_id in MAIN_STAGE_IDS and next_step_id not in REPAIR_STAGE_IDS and next_step_id != current_step_id:
        if current_step_id not in state.completed_stages:
            state.completed_stages.append(current_step_id)

    if current_step_id in REPAIR_STAGE_IDS and next_step_id == state.return_stage_id:
        state.return_stage_id = None
        state.repair_context = {}

    state.current_stage_id = next_step_id


def _record_success_payload(
    state: AcademicResearchPipelineState,
    *,
    current_step_id: str,
    output: dict,
) -> None:
    if current_step_id == "collect_research_context":
        state.research_goal = output.get("research_goal") or state.research_goal
        state.entry_stage = output.get("entry_stage") or state.entry_stage
        state.available_materials = list(output.get("available_materials") or [])
        state.paper_path = output.get("paper_path") or state.paper_path
        state.material_passport_path = output.get("material_passport_path") or state.material_passport_path
        state.output_dir = output.get("output_dir") or state.output_dir
    elif current_step_id == "plan_academic_pipeline":
        state.stage_plan = list(output.get("stage_plan") or [])
        state.next_stage = output.get("next_stage")
        state.mode_selection = dict(output.get("mode_selection") or {})
    elif current_step_id == "run_research_stage":
        state.research_artifact_paths = _string_list(output.get("research_artifact_paths"))
    elif current_step_id == "run_write_stage":
        state.draft_path = output.get("draft_path")
        state.paper_path = output.get("draft_path") or state.paper_path
    elif current_step_id == "run_pre_review_integrity":
        state.integrity_passed = output.get("integrity_passed")
        state.material_passport_path = output.get("material_passport_path") or state.material_passport_path
    elif current_step_id == "run_review_stage":
        state.review_package_path = output.get("review_package_path")
        state.revision_roadmap_path = output.get("revision_roadmap_path")
        state.editorial_decision = output.get("editorial_decision")
    elif current_step_id == "run_revision_stage":
        state.revised_draft_path = output.get("revised_draft_path")
        state.paper_path = output.get("revised_draft_path") or state.paper_path
        state.revision_loop_count = _positive_int(output.get("revision_loop_count"), default=state.revision_loop_count)
    elif current_step_id == "run_rereview_stage":
        state.rereview_package_path = output.get("rereview_package_path")
        state.rereview_decision = output.get("rereview_decision")
    elif current_step_id == "run_final_integrity":
        state.final_integrity_passed = output.get("final_integrity_passed")
        state.material_passport_path = output.get("material_passport_path") or state.material_passport_path
        state.final_integrity_report_path = output.get("final_integrity_report_path")
    elif current_step_id == "finalize_publication_package":
        state.output_package_paths = _string_list(output.get("output_package_paths"))
    elif current_step_id == "generate_process_summary":
        state.process_summary_path = output.get("process_summary_path")


def _build_repair_context(
    *,
    current_step_id: str,
    return_stage_id: str,
    transition_reason: str,
    repair_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "source_stage_id": current_step_id,
        "return_stage_id": return_stage_id,
        "transition_reason": transition_reason,
        "repair_payload": dict(repair_payload or {}),
    }


def _build_agent_repair_payload(
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> dict[str, object] | None:
    default_payload = build_default_agent_repair_payload(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    if default_payload is not None:
        return default_payload

    output = observation.get("structured_output") or {}
    if not isinstance(output, dict):
        return None

    if current_step_id == "run_pre_review_integrity" and output.get("integrity_passed") is False:
        requirements = _string_list(output.get("suspected_failure_modes"))
        evidence = _issue_titles(output.get("critical_issues"))
        return make_agent_repair_payload(
            category="business_rule_failed",
            summary="Stage 2.5 integrity gate did not pass.",
            requirements=requirements,
            evidence=evidence,
        )

    if current_step_id == "run_final_integrity" and output.get("final_integrity_passed") is False:
        requirements = _string_list(output.get("suspected_failure_modes"))
        evidence = _issue_titles(output.get("critical_issues")) + _issue_titles(output.get("residual_issues"))
        return make_agent_repair_payload(
            category="business_rule_failed",
            summary="Stage 4.5 final integrity gate did not pass.",
            requirements=requirements,
            evidence=evidence,
        )

    return None


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


def _positive_int(value, *, default: int) -> int:
    return value if isinstance(value, int) and value >= 0 else default


def _issue_titles(value) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        text = str(item.get("issue") or item.get("summary") or "").strip()
        if text:
            items.append(text)
        if len(items) >= 3:
            break
    return items


def _normalize_decision(value) -> str:
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "accept": "accept",
        "accepted": "accept",
        "minor": "minor_revision",
        "minor_revision": "minor_revision",
        "major": "major_revision",
        "major_revision": "major_revision",
        "reject": "reject",
        "rejected": "reject",
    }
    return aliases.get(text, text)
