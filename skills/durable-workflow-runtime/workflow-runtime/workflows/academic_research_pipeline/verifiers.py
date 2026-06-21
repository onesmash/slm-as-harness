from __future__ import annotations

from pathlib import Path

from workflows.common.contracts import VerifierResult, make_verifier_result


ALLOWED_ENTRY_STAGES = {
    "research",
    "write",
    "pre_review_integrity",
    "review",
    "revision",
    "rereview",
    "final_integrity",
    "finalize",
    "process_summary",
    "stage_1",
    "stage_2",
    "stage_2_5",
    "stage_3",
    "stage_4",
    "stage_3_prime",
    "stage_4_5",
    "stage_5",
    "stage_6",
}
ALLOWED_REVIEW_DECISIONS = {"accept", "minor_revision", "major_revision", "reject"}
ALLOWED_REREVIEW_DECISIONS = {"accept", "minor_revision", "major_revision"}


def verify_collect_research_context(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    if observation.get("status") == "blocked":
        return _verify_blocked_payload(output, run_id, step_id, state, "research context collection")
    if not _non_empty_string(output.get("research_goal")):
        return _fail("research_goal must be a non-empty string", run_id, step_id, state)
    if _normalize(output.get("entry_stage")) not in ALLOWED_ENTRY_STAGES:
        return _fail("entry_stage is not supported", run_id, step_id, state)
    if not isinstance(output.get("available_materials"), list):
        return _fail("available_materials must be a list", run_id, step_id, state)
    if _string_list(output.get("missing_inputs")) is None:
        return _fail("missing_inputs must be a list of strings", run_id, step_id, state)
    if _string_list(output.get("open_questions")) is None:
        return _fail("open_questions must be a list of strings", run_id, step_id, state)
    if output.get("ready_for_pipeline") is not True:
        return _fail("ready_for_pipeline must be true before planning", run_id, step_id, state)
    return _pass("research context output accepted", repo_root, run_id, step_id)


def verify_plan_academic_pipeline(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    stage_plan = output.get("stage_plan")
    if not isinstance(stage_plan, list) or not stage_plan:
        return _fail("stage_plan must be a non-empty list", run_id, step_id, state)
    if _normalize(output.get("next_stage")) not in ALLOWED_ENTRY_STAGES:
        return _fail("next_stage is not supported", run_id, step_id, state)
    if not isinstance(output.get("mode_selection"), dict):
        return _fail("mode_selection must be an object", run_id, step_id, state)
    checkpoint_policy = output.get("checkpoint_policy")
    if not isinstance(checkpoint_policy, dict) or not checkpoint_policy:
        return _fail("checkpoint_policy must be a non-empty object", run_id, step_id, state)
    if output.get("user_confirmed_plan") is not True:
        return _fail("user_confirmed_plan must be true before execution", run_id, step_id, state)
    return _pass("academic pipeline plan accepted", repo_root, run_id, step_id)


def verify_run_research_stage(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    paths = _string_list(output.get("research_artifact_paths"))
    if not paths:
        return _fail("research_artifact_paths must be a non-empty list of strings", run_id, step_id, state)
    if not _non_empty_string(output.get("research_summary")):
        return _fail("research_summary must be a non-empty string", run_id, step_id, state)
    if not isinstance(output.get("source_verification_summary"), dict):
        return _fail("source_verification_summary must be an object", run_id, step_id, state)
    if output.get("user_confirmed_checkpoint") is not True:
        return _fail("user_confirmed_checkpoint must be true after Stage 1", run_id, step_id, state)
    if output.get("ready_for_write") is not True:
        return _fail("ready_for_write must be true before Stage 2", run_id, step_id, state)
    return _pass("research stage output accepted", repo_root, run_id, step_id)


def verify_run_write_stage(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    draft_path = output.get("draft_path")
    if not _non_empty_string(draft_path):
        return _fail("draft_path must be a non-empty string", run_id, step_id, state)
    if not Path(draft_path).exists():
        return _fail("draft_path must point to an existing file", run_id, step_id, state)
    if not isinstance(output.get("citation_audit_summary"), dict):
        return _fail("citation_audit_summary must be an object", run_id, step_id, state)
    if output.get("user_confirmed_checkpoint") is not True:
        return _fail("user_confirmed_checkpoint must be true after Stage 2", run_id, step_id, state)
    if output.get("ready_for_integrity") is not True:
        return _fail("ready_for_integrity must be true before Stage 2.5", run_id, step_id, state)
    return _pass("write stage output accepted", repo_root, run_id, step_id)


def verify_run_pre_review_integrity(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    if not isinstance(output.get("integrity_passed"), bool):
        return _fail("integrity_passed must be a boolean", run_id, step_id, state)
    if not _non_empty_string(output.get("material_passport_path")):
        return _fail("material_passport_path must be a non-empty string", run_id, step_id, state)
    suspected = _string_list(output.get("suspected_failure_modes"))
    if suspected is None:
        return _fail("suspected_failure_modes must be a list of strings", run_id, step_id, state)
    if output.get("integrity_passed") is True and suspected:
        return _fail("passed integrity gate cannot include suspected failure modes", run_id, step_id, state)
    if output.get("user_acknowledged_gate") is not True:
        return _fail("user_acknowledged_gate must be true for Stage 2.5", run_id, step_id, state)
    return _pass("pre-review integrity output accepted", repo_root, run_id, step_id)


def verify_run_review_stage(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    if not _non_empty_string(output.get("review_package_path")):
        return _fail("review_package_path must be a non-empty string", run_id, step_id, state)
    decision = _normalize_decision(output.get("editorial_decision"))
    if decision not in ALLOWED_REVIEW_DECISIONS:
        return _fail("editorial_decision is not supported", run_id, step_id, state)
    if not isinstance(output.get("critical_issues"), list):
        return _fail("critical_issues must be a list", run_id, step_id, state)
    if decision != "accept" and not _non_empty_string(output.get("revision_roadmap_path")):
        return _fail("non-accept decisions must include revision_roadmap_path", run_id, step_id, state)
    if output.get("user_confirmed_checkpoint") is not True:
        return _fail("user_confirmed_checkpoint must be true after Stage 3", run_id, step_id, state)
    return _pass("review stage output accepted", repo_root, run_id, step_id)


def verify_run_revision_stage(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    revised_draft_path = output.get("revised_draft_path")
    if not _non_empty_string(revised_draft_path):
        return _fail("revised_draft_path must be a non-empty string", run_id, step_id, state)
    if not Path(revised_draft_path).exists():
        return _fail("revised_draft_path must point to an existing file", run_id, step_id, state)
    if not isinstance(output.get("revision_loop_count"), int) or output["revision_loop_count"] < 1:
        return _fail("revision_loop_count must be a positive integer", run_id, step_id, state)
    if output.get("user_confirmed_checkpoint") is not True:
        return _fail("user_confirmed_checkpoint must be true after revision", run_id, step_id, state)
    if output.get("revision_complete") is not True:
        return _fail("revision_complete must be true before re-review", run_id, step_id, state)
    return _pass("revision stage output accepted", repo_root, run_id, step_id)


def verify_run_rereview_stage(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    if not _non_empty_string(output.get("rereview_package_path")):
        return _fail("rereview_package_path must be a non-empty string", run_id, step_id, state)
    decision = _normalize_decision(output.get("rereview_decision"))
    if decision not in ALLOWED_REREVIEW_DECISIONS:
        return _fail("rereview_decision is not supported", run_id, step_id, state)
    if not isinstance(output.get("residual_issues"), list):
        return _fail("residual_issues must be a list", run_id, step_id, state)
    if not isinstance(output.get("ready_for_final_integrity"), bool):
        return _fail("ready_for_final_integrity must be a boolean", run_id, step_id, state)
    return _pass("re-review stage output accepted", repo_root, run_id, step_id)


def verify_run_final_integrity(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    if not isinstance(output.get("final_integrity_passed"), bool):
        return _fail("final_integrity_passed must be a boolean", run_id, step_id, state)
    if not _non_empty_string(output.get("material_passport_path")):
        return _fail("material_passport_path must be a non-empty string", run_id, step_id, state)
    high_warn = _string_list(output.get("high_warn_annotations"))
    if high_warn is None:
        return _fail("high_warn_annotations must be a list of strings", run_id, step_id, state)
    if output.get("final_integrity_passed") is True and high_warn:
        return _fail("passed final integrity cannot include high-warn annotations", run_id, step_id, state)
    if output.get("user_acknowledged_gate") is not True:
        return _fail("user_acknowledged_gate must be true for Stage 4.5", run_id, step_id, state)
    return _pass("final integrity output accepted", repo_root, run_id, step_id)


def verify_finalize_publication_package(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    paths = _string_list(output.get("output_package_paths"))
    if not paths:
        return _fail("output_package_paths must be a non-empty list of strings", run_id, step_id, state)
    if not _non_empty_string(output.get("format_selected")):
        return _fail("format_selected must be a non-empty string", run_id, step_id, state)
    if output.get("final_package_ready") is not True:
        return _fail("final_package_ready must be true before process summary", run_id, step_id, state)
    return _pass("final publication package accepted", repo_root, run_id, step_id)


def verify_generate_process_summary(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    if not _non_empty_string(output.get("process_summary_path")):
        return _fail("process_summary_path must be a non-empty string", run_id, step_id, state)
    if output.get("collaboration_quality_reviewed") is not True:
        return _fail("collaboration_quality_reviewed must be true", run_id, step_id, state)
    if output.get("summary_ready") is not True:
        return _fail("summary_ready must be true before final summary", run_id, step_id, state)
    return _pass("process summary output accepted", repo_root, run_id, step_id)


def _verify_blocked_payload(
    output: dict,
    run_id: str,
    step_id: str,
    state: dict | None,
    stage_name: str,
) -> VerifierResult:
    if not _non_empty_string(output.get("blocked_reason")):
        return _fail(f"blocked {stage_name} must include blocked_reason", run_id, step_id, state)
    missing_inputs = _string_list(output.get("missing_inputs"))
    open_questions = _string_list(output.get("open_questions"))
    if missing_inputs is None:
        return _fail("missing_inputs must be a list of strings when provided", run_id, step_id, state)
    if open_questions is None:
        return _fail("open_questions must be a list of strings when provided", run_id, step_id, state)
    if not missing_inputs and not open_questions:
        return _fail(f"blocked {stage_name} must include missing_inputs or open_questions", run_id, step_id, state)
    return make_verifier_result(
        passed=True,
        message=f"blocked {stage_name} payload accepted",
        details={"run_id": run_id, "step_id": step_id},
    )


def _output(observation: dict) -> dict:
    structured_output = observation.get("structured_output") or {}
    return structured_output if isinstance(structured_output, dict) else {}


def _string_list(value) -> list[str] | None:
    if value is None:
        return []
    if not isinstance(value, list):
        return None
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        text = item.strip()
        if text:
            normalized.append(text)
    return normalized


def _non_empty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize(value) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")


def _normalize_decision(value) -> str:
    text = _normalize(value)
    aliases = {
        "accepted": "accept",
        "minor": "minor_revision",
        "major": "major_revision",
        "rejected": "reject",
    }
    return aliases.get(text, text)


def _pass(message: str, repo_root: str, run_id: str, step_id: str) -> VerifierResult:
    return make_verifier_result(
        passed=True,
        message=message,
        details={"repo_root": repo_root, "run_id": run_id, "step_id": step_id},
    )


def _fail(message: str, run_id: str, step_id: str, state: dict | None) -> VerifierResult:
    return make_verifier_result(
        passed=False,
        message=message,
        details={
            "run_id": run_id,
            "step_id": step_id,
            "state": state or {},
        },
    )
