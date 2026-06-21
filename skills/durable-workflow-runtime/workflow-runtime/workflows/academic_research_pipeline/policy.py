from __future__ import annotations

from workflows.common.policies import TransitionDecision


STAGE_TO_NODE = {
    "research": "run_research_stage",
    "stage_1": "run_research_stage",
    "write": "run_write_stage",
    "stage_2": "run_write_stage",
    "pre_review_integrity": "run_pre_review_integrity",
    "stage_2_5": "run_pre_review_integrity",
    "review": "run_review_stage",
    "stage_3": "run_review_stage",
    "revision": "run_revision_stage",
    "stage_4": "run_revision_stage",
    "rereview": "run_rereview_stage",
    "stage_3_prime": "run_rereview_stage",
    "final_integrity": "run_final_integrity",
    "stage_4_5": "run_final_integrity",
    "finalize": "finalize_publication_package",
    "stage_5": "finalize_publication_package",
    "process_summary": "generate_process_summary",
    "stage_6": "generate_process_summary",
}


def choose_next_node(
    *,
    current_step_id: str,
    state: dict,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision:
    if current_step_id == "collect_research_context":
        status_decision = _route_common_failure(
            observation=observation,
            current_step_id=current_step_id,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        output = observation.get("structured_output") or {}
        if output.get("ready_for_pipeline") is not True:
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="academic research context is not ready for pipeline planning",
            )
        return TransitionDecision(
            next_node="plan_academic_pipeline",
            branch_kind="continue",
            reason="research context is ready for ARS stage planning",
        )

    if current_step_id == "plan_academic_pipeline":
        status_decision = _route_common_failure(
            observation=observation,
            current_step_id=current_step_id,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        output = observation.get("structured_output") or {}
        next_node = STAGE_TO_NODE.get(_normalize_stage(output.get("next_stage")))
        if next_node is None:
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="pipeline plan did not provide a supported next_stage",
            )
        return TransitionDecision(
            next_node=next_node,
            branch_kind="continue",
            reason=f"pipeline plan selected {next_node}",
        )

    if current_step_id == "run_research_stage":
        return _route_main_stage(
            current_step_id=current_step_id,
            next_node="run_write_stage",
            observation=observation,
            verifier_result=verifier_result,
        )

    if current_step_id == "run_write_stage":
        return _route_main_stage(
            current_step_id=current_step_id,
            next_node="run_pre_review_integrity",
            observation=observation,
            verifier_result=verifier_result,
        )

    if current_step_id == "run_pre_review_integrity":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        output = observation.get("structured_output") or {}
        if output.get("integrity_passed") is not True:
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="Stage 2.5 integrity gate must pass before review",
            )
        return TransitionDecision(
            next_node="run_review_stage",
            branch_kind="continue",
            reason="pre-review integrity gate passed",
        )

    if current_step_id == "run_review_stage":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        output = observation.get("structured_output") or {}
        decision = _normalize_decision(output.get("editorial_decision"))
        if decision == "accept":
            return TransitionDecision(
                next_node="run_final_integrity",
                branch_kind="continue",
                reason="review accepted the paper",
            )
        if decision in {"minor_revision", "major_revision"}:
            return TransitionDecision(
                next_node="run_revision_stage",
                branch_kind="continue",
                reason=f"review requires {decision}",
            )
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason="review decision is reject or unsupported; pipeline needs user direction",
        )

    if current_step_id == "run_revision_stage":
        return _route_main_stage(
            current_step_id=current_step_id,
            next_node="run_rereview_stage",
            observation=observation,
            verifier_result=verifier_result,
        )

    if current_step_id == "run_rereview_stage":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        output = observation.get("structured_output") or {}
        if output.get("ready_for_final_integrity") is True:
            return TransitionDecision(
                next_node="run_final_integrity",
                branch_kind="continue",
                reason="re-review cleared the paper for final integrity",
            )
        if int(state.get("revision_loop_count") or 0) < int(state.get("max_revision_loops") or 2):
            return TransitionDecision(
                next_node="run_revision_stage",
                branch_kind="continue",
                reason="residual issues require the final revision loop",
            )
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason="re-review found residual issues after revision loop budget",
        )

    if current_step_id == "run_final_integrity":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        output = observation.get("structured_output") or {}
        if output.get("final_integrity_passed") is not True:
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="Stage 4.5 final integrity gate must pass before finalization",
            )
        return TransitionDecision(
            next_node="finalize_publication_package",
            branch_kind="continue",
            reason="final integrity gate passed",
        )

    if current_step_id == "finalize_publication_package":
        return _route_main_stage(
            current_step_id=current_step_id,
            next_node="generate_process_summary",
            observation=observation,
            verifier_result=verifier_result,
        )

    if current_step_id == "generate_process_summary":
        return _route_main_stage(
            current_step_id=current_step_id,
            next_node="finalize_summary",
            observation=observation,
            verifier_result=verifier_result,
        )

    if current_step_id == "request_unblocking_input":
        if observation["status"] == "succeeded":
            return TransitionDecision(
                next_node=state.get("return_stage_id") or "plan_academic_pipeline",
                branch_kind="continue",
                reason="user supplied the input needed to continue the blocked stage",
            )
        return TransitionDecision(
            next_node="request_unblocking_input",
            branch_kind="repair",
            reason="blocking details are still unresolved",
        )

    if current_step_id == "repair_and_resume":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node="request_unblocking_input",
                branch_kind="repair",
                reason="repair is blocked and needs external help",
            )
        if observation["status"] == "succeeded":
            return TransitionDecision(
                next_node=state.get("return_stage_id") or "plan_academic_pipeline",
                branch_kind="continue",
                reason="repair work is complete and the original stage can resume",
            )
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason="repair stage still needs more iteration",
        )

    raise LookupError(f"no transition policy for step: {current_step_id}")


def _route_main_stage(
    *,
    current_step_id: str,
    next_node: str,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision:
    status_decision = _route_common_failure(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    if status_decision is not None:
        return status_decision
    return TransitionDecision(
        next_node=next_node,
        branch_kind="continue" if next_node != "finalize_summary" else "complete",
        reason=f"{current_step_id} completed successfully",
    )


def _route_common_failure(
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision | None:
    if observation["status"] == "blocked":
        return TransitionDecision(
            next_node="request_unblocking_input",
            branch_kind="repair",
            reason=f"{current_step_id} is blocked and needs user help",
        )
    if observation["status"] == "partial":
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason=f"{current_step_id} only partially completed",
        )
    if observation["status"] == "failed":
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason=f"{current_step_id} failed and should be retried",
        )
    if verifier_result is not None and not verifier_result["passed"]:
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason=f"{current_step_id} did not satisfy verifier checks",
        )
    return None


def _normalize_stage(value) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")


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
