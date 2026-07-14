from __future__ import annotations

from workflows.common.policies import TransitionDecision, condition_matches


def choose_next_node(
    *,
    current_step_id: str,
    state: dict,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision:
    if current_step_id == "brainstorm_optimization":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="research_optimization",
            branch_kind="continue",
            reason="brainstorm_optimization completed; continue to research_optimization",
        )

    if current_step_id == "research_optimization":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="plan_optimization",
            branch_kind="continue",
            reason="research_optimization completed; continue to plan_optimization",
        )

    if current_step_id == "plan_optimization":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="implement_optimization",
            branch_kind="continue",
            reason="plan_optimization completed; continue to implement_optimization",
        )

    if current_step_id == "implement_optimization":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="review_optimization",
            branch_kind="continue",
            reason="implement_optimization completed; continue to review_optimization",
        )

    if current_step_id == "review_optimization":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="update_optimization_knowledge_base",
            branch_kind="continue",
            reason="review_optimization completed; continue to update_optimization_knowledge_base",
        )

    if current_step_id == "update_optimization_knowledge_base":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('continue_optimization'), 'is_true', None):
                return TransitionDecision(
                    next_node='brainstorm_optimization',
                    branch_kind='continue',
                    reason='Knowledge-base maintenance requested another optimization iteration.',
                )
        return TransitionDecision(
            next_node="finalize_optimization_cycle",
            branch_kind="complete",
            reason="update_optimization_knowledge_base completed successfully",
        )

    if current_step_id == "request_unblocking_input":
        if observation["status"] == "succeeded":
            return_stage_id = state.get("return_stage_id")
            repair_context = state.get("repair_context") or {}
            source_stage_id = repair_context.get("source_stage_id")
            resume_target = "repair_and_resume" if source_stage_id == "repair_and_resume" else return_stage_id
            if not resume_target:
                return TransitionDecision(
                    next_node="request_unblocking_input",
                    branch_kind="repair",
                    reason="cannot resume because the next recovery target is missing",
                )
            return TransitionDecision(
                next_node=resume_target,
                branch_kind="continue",
                reason="user supplied the missing input and the workflow can return to the recovery owner",
            )
        return TransitionDecision(
            next_node="request_unblocking_input",
            branch_kind="repair",
            reason="blocking details are still unresolved",
        )

    if current_step_id == "repair_and_resume":
        if observation["status"] == "blocked":
            repair_attempts = int((state.get("attempt_counts") or {}).get("repair_and_resume") or 0)
            if repair_attempts < 3:
                return TransitionDecision(
                    next_node="repair_and_resume",
                    branch_kind="retry",
                    reason="repair must attempt self-repair at least 3 times before requesting external help",
                )
            return TransitionDecision(
                next_node="request_unblocking_input",
                branch_kind="repair",
                reason="repair exhausted 3 self-repair attempts and now requires external help before retry",
            )
        if observation["status"] == "succeeded":
            return_stage_id = state.get("return_stage_id")
            if not return_stage_id:
                return TransitionDecision(
                    next_node="repair_and_resume",
                    branch_kind="retry",
                    reason="cannot resume because return_stage_id is missing",
                )
            return TransitionDecision(
                next_node=return_stage_id,
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
            next_node="repair_and_resume",
            branch_kind="repair",
            reason=f"{current_step_id} is blocked and should be triaged by shared repair first",
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
