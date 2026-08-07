from __future__ import annotations

from workflows.common.policies import (
    TransitionDecision,
    condition_matches,
    max_steps_exceeded_decision,
)


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

    if current_step_id == "warm_start_shared_space":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="warm_start_shared_space completed without a passing verifier result",
            )
        return TransitionDecision(
            next_node="launch_expert_subagents",
            branch_kind="continue",
            reason="warm_start_shared_space completed; continue to launch_expert_subagents",
        )

    if current_step_id == "launch_expert_subagents":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="launch_expert_subagents completed without a passing verifier result",
            )
        return TransitionDecision(
            next_node="autonomous_roundtable",
            branch_kind="continue",
            reason="launch_expert_subagents completed; continue to autonomous_roundtable",
        )

    if current_step_id == "autonomous_roundtable":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="autonomous_roundtable completed without a passing verifier result",
            )
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('should_reorganize'), 'is_true', None):
                return TransitionDecision(
                    next_node='reorganize_knowledge_space',
                    branch_kind='reorganize',
                    reason='Moderator selected knowledge-space reorganization before another roundtable turn.',
                )
            if condition_matches(structured_output.get('ready_for_report'), 'is_true', None):
                return TransitionDecision(
                    next_node='synthesize_report',
                    branch_kind='complete_research',
                    reason='Moderator determined that coverage or the autonomous research budget justifies report synthesis.',
                )
            if condition_matches(structured_output.get('continue_roundtable'), 'is_true', None):
                return TransitionDecision(
                    next_node='launch_expert_subagents',
                    branch_kind='continue',
                    reason='Moderator selected another autonomous roundtable turn; collect a fresh result for each expert first.',
                )
        return TransitionDecision(
            next_node="autonomous_roundtable",
            branch_kind="retry",
            reason="autonomous_roundtable did not match a declared business transition; retry the stage",
        )

    if current_step_id == "reorganize_knowledge_space":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="reorganize_knowledge_space completed without a passing verifier result",
            )
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('reorganized'), 'is_true', None):
                return TransitionDecision(
                    next_node='launch_expert_subagents',
                    branch_kind='continue',
                    reason='Knowledge-space maintenance completed; return the updated map for the next expert-result round.',
                )
        return TransitionDecision(
            next_node="reorganize_knowledge_space",
            branch_kind="retry",
            reason="reorganize_knowledge_space did not match a declared business transition; retry the stage",
        )

    if current_step_id == "synthesize_report":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="synthesize_report completed without a passing verifier result",
            )
        return TransitionDecision(
            next_node="verify_report",
            branch_kind="continue",
            reason="synthesize_report completed; continue to verify_report",
        )

    if current_step_id == "verify_report":
        if observation["status"] == "succeeded" and not isinstance(verifier_result, dict):
            return TransitionDecision(
                next_node='repair_and_resume',
                branch_kind='repair',
                reason='verify_report completed without a verifier result; fail closed and preserve the report for recovery.',
            )
        if observation["status"] == "succeeded" and isinstance(verifier_result, dict) and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node='repair_report',
                branch_kind='repair',
                reason='The report quality or citation verifier found a repairable defect; route to report-specific repair before re-synthesis.',
            )
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="retry",
                reason="verify_report completed without a passing verifier result",
            )
        return TransitionDecision(
            next_node="finalize_collaborative_report",
            branch_kind="complete",
            reason="verify_report completed successfully",
        )

    if current_step_id == "repair_report":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="repair",
                reason="repair_report is blocked and should be triaged by shared repair first",
            )
        if observation["status"] == "succeeded" and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_report",
                branch_kind="retry",
                reason="repair_report repair output did not satisfy verifier checks",
            )
        if observation["status"] in ('partial', 'failed'):
            return TransitionDecision(
                next_node="repair_report",
                branch_kind="retry",
                reason="repair_report recovery stage still needs more iteration",
            )
        if observation["status"] == "succeeded":
            return TransitionDecision(
                next_node="synthesize_report",
                branch_kind="continue",
                reason="repair_report completed recovery work; return to synthesize_report",
            )
        return TransitionDecision(
            next_node="repair_report",
            branch_kind="retry",
            reason="repair_report recovery stage returned an unresolved status",
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
            raw_repair_attempts = state.get("repair_blocked_attempts")
            if not isinstance(raw_repair_attempts, int) or isinstance(raw_repair_attempts, bool):
                raw_attempt_counts = state.get("attempt_counts")
                raw_repair_attempts = raw_attempt_counts.get("repair_and_resume") if isinstance(raw_attempt_counts, dict) else None
            repair_attempts = raw_repair_attempts if isinstance(raw_repair_attempts, int) and not isinstance(raw_repair_attempts, bool) else 0
            if repair_attempts < 3:
                return TransitionDecision(
                    next_node="repair_and_resume",
                    branch_kind="retry",
                    reason="repair must attempt self-repair at least 3 times before the configured terminal handoff",
                )
            return TransitionDecision(
                next_node='finalize_collaborative_report',
                branch_kind='partial',
                reason='repair exhausted 3 self-repair attempts; terminate with a partial handoff instead of waiting for user input',
            )
        if observation["status"] == "succeeded":
            structured_output = observation.get("structured_output") or {}
            if not _repair_output_is_complete(structured_output, state):
                return TransitionDecision(
                    next_node="repair_and_resume",
                    branch_kind="retry",
                    reason="repair_and_resume succeeded without a complete retry plan",
                )
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
    if verifier_result is not None and not _verifier_is_passed(verifier_result):
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="retry",
            reason=f"{current_step_id} did not satisfy verifier checks",
        )
    return None


def _verifier_is_passed(verifier_result: dict | None) -> bool:
    return isinstance(verifier_result, dict) and verifier_result.get("passed") is True


def _repair_output_is_complete(output: dict, state: dict) -> bool:
    if not isinstance(output, dict):
        return False
    repair_context = state.get("repair_context") if isinstance(state, dict) else None
    if not isinstance(repair_context, dict):
        return False
    repair_payload = repair_context.get("repair_payload")
    if not isinstance(repair_payload, dict) or not str(repair_payload.get("summary") or "").strip():
        return False
    for key in ("retry_reason", "retry_notes"):
        value = output.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
    actions = output.get("repair_actions")
    return (
        isinstance(actions, list)
        and bool(actions)
        and all(isinstance(action, str) and action.strip() for action in actions)
    )
