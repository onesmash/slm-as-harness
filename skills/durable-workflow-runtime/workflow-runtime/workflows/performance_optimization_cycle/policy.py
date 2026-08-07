from __future__ import annotations

from workflows.common.policies import (
    TransitionDecision,
    condition_matches,
    max_steps_exceeded_decision,
)

MAX_SELF_REPAIR_ATTEMPTS = 3


def choose_next_node(
    *,
    current_step_id: str,
    state: dict,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision:
    budget_decision = max_steps_exceeded_decision(
        current_step_id=current_step_id,
        state=state,
    )
    if budget_decision is not None:
        return budget_decision

    if current_step_id == "diagnose_performance":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node='capture_blocked_cycle_knowledge',
                branch_kind='continue',
                reason='A blocked diagnosis must be recorded in the knowledge base before a fresh optimization cycle begins; do not request user unblocking input.',
            )
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="brainstorm_optimization",
            branch_kind="continue",
            reason="diagnose_performance completed; continue to brainstorm_optimization",
        )

    if current_step_id == "brainstorm_optimization":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node='capture_blocked_cycle_knowledge',
                branch_kind='continue',
                reason='A blocked ideation stage must be recorded in the knowledge base before a fresh optimization cycle begins; do not request user unblocking input.',
            )
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
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node='capture_blocked_cycle_knowledge',
                branch_kind='continue',
                reason='A blocked research stage must be recorded in the knowledge base before a fresh optimization cycle begins; do not request user unblocking input.',
            )
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
            reason="research_optimization completed; continue to implement_optimization",
        )

    if current_step_id == "implement_optimization":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node='capture_blocked_cycle_knowledge',
                branch_kind='continue',
                reason='A blocked implementation stage must be recorded in the knowledge base before a fresh optimization cycle begins; do not request user unblocking input.',
            )
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
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node='capture_blocked_cycle_knowledge',
                branch_kind='continue',
                reason='A blocked review stage must be recorded in the knowledge base before a fresh optimization cycle begins; do not request user unblocking input.',
            )
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
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node='capture_blocked_cycle_knowledge',
                branch_kind='continue',
                reason='A blocked knowledge-base update must immediately begin a fresh optimization cycle rather than request user unblocking input.',
            )
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="update_optimization_knowledge_base completed without a passing verifier result",
            )
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
                raw_completed_cycles = state.get("completed_optimization_cycles")
                completed_cycles = (
                    raw_completed_cycles
                    if isinstance(raw_completed_cycles, int)
                    and not isinstance(raw_completed_cycles, bool)
                    else 0
                )
                max_cycles = _max_cycles(state)
                if completed_cycles >= max_cycles:
                    return TransitionDecision(
                        next_node='finalize_optimization_cycle',
                        branch_kind='complete',
                        reason=f'Knowledge-base maintenance requested another iteration, but the configured max_cycles={max_cycles} limit has been reached.',
                    )
                return TransitionDecision(
                    next_node='diagnose_performance',
                    branch_kind='continue',
                    reason='Knowledge-base maintenance requested another optimization iteration, so performance must be re-diagnosed.',
                )
        return TransitionDecision(
            next_node="finalize_optimization_cycle",
            branch_kind="complete",
            reason="update_optimization_knowledge_base completed successfully",
        )

    if current_step_id == "capture_blocked_cycle_knowledge":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node='diagnose_performance',
                branch_kind='continue',
                reason='Knowledge-base capture is unavailable; retain the runtime blocker and begin a fresh diagnosis without requesting user input.',
            )
        if observation["status"] == "partial":
            return TransitionDecision(
                next_node='diagnose_performance',
                branch_kind='continue',
                reason='Knowledge-base capture is incomplete; retain its runtime evidence and begin a fresh diagnosis without requesting user input.',
            )
        if observation["status"] == "failed":
            return TransitionDecision(
                next_node='diagnose_performance',
                branch_kind='continue',
                reason='Knowledge-base capture failed; retain its runtime evidence and begin a fresh diagnosis without requesting user input.',
            )
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node='diagnose_performance',
                branch_kind='continue',
                reason='Knowledge-base capture could not be verified; retain its runtime evidence and begin a fresh diagnosis without requesting user input.',
            )
        if observation["status"] == "succeeded":
            return TransitionDecision(
                next_node="diagnose_performance",
                branch_kind="continue",
                reason="capture_blocked_cycle_knowledge completed recovery work; return to diagnose_performance",
            )
        return TransitionDecision(
            next_node="capture_blocked_cycle_knowledge",
            branch_kind="retry",
            reason="capture_blocked_cycle_knowledge recovery stage returned an unresolved status",
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
            raw_attempt_counts = state.get("attempt_counts")
            raw_repair_attempts = (
                raw_attempt_counts.get("repair_and_resume")
                if isinstance(raw_attempt_counts, dict)
                else None
            )
            repair_attempts = (
                raw_repair_attempts
                if isinstance(raw_repair_attempts, int) and not isinstance(raw_repair_attempts, bool)
                else 0
            )
            if repair_attempts < MAX_SELF_REPAIR_ATTEMPTS:
                return TransitionDecision(
                    next_node="repair_and_resume",
                    branch_kind="retry",
                    reason=f"repair must attempt self-repair at least {MAX_SELF_REPAIR_ATTEMPTS} times before requesting external help",
                )
            return TransitionDecision(
                next_node="request_unblocking_input",
                branch_kind="repair",
                reason=f"repair exhausted {MAX_SELF_REPAIR_ATTEMPTS} self-repair attempts and now requires external help before retry",
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


def _max_cycles(state: dict) -> int:
    constraints = state.get("constraints") if isinstance(state, dict) else {}
    value = constraints.get("max_cycles") if isinstance(constraints, dict) else None
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return 3


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
    if verifier_result is not None and not _verifier_is_passed(verifier_result):
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason=f"{current_step_id} did not satisfy verifier checks",
        )
    return None


def _verifier_is_passed(verifier_result: dict | None) -> bool:
    return isinstance(verifier_result, dict) and verifier_result.get("passed") is True
