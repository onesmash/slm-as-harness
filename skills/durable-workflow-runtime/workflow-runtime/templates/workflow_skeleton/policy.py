from __future__ import annotations

from workflows.common.policies import TransitionDecision


def choose_next_node(
    *,
    current_step_id: str,
    state: dict,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision:
    if current_step_id == "run_primary_stage":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="finalize_summary",
            branch_kind="complete",
            reason="primary stage completed successfully",
        )

    if current_step_id == "request_unblocking_input":
        if observation["status"] == "succeeded":
            return TransitionDecision(
                next_node=state.get("return_stage_id") or "run_primary_stage",
                branch_kind="continue",
                reason="user supplied the missing input and the original stage can resume",
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
                reason="retry is blocked and requires external help",
            )
        if observation["status"] == "succeeded":
            return TransitionDecision(
                next_node=state.get("return_stage_id") or "run_primary_stage",
                branch_kind="continue",
                reason="repair work is complete and the original stage can resume",
            )
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason="repair stage still needs more iteration",
        )

    raise LookupError(f"no transition policy for step: {current_step_id}")


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
