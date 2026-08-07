from __future__ import annotations

from workflows.common.policies import TransitionDecision, condition_matches

from . import state as workflow_state


_MISSING_VERIFIER_REASONS = {
    stage_id: f"{stage_id} completed without a valid verifier result; fail closed before continuing."
    for stage_id in workflow_state.MAIN_STAGE_IDS
}


def choose_next_node(
    *,
    current_step_id: str,
    state: dict,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision:
    max_steps_decision = workflow_state.max_steps_exceeded_decision(
        current_step_id=current_step_id,
        state=state,
    )
    if max_steps_decision is not None:
        return TransitionDecision(
            next_node="finalize_delivery_summary",
            branch_kind="complete",
            reason=(
                f"{max_steps_decision.reason}; terminate with a degraded final summary"
            ),
            metadata={
                **max_steps_decision.metadata,
                "degraded": True,
                "terminal_reason": "max_steps_exceeded",
            },
        )

    if (
        current_step_id in workflow_state.MAIN_STAGE_IDS
        and observation.get("status") == "succeeded"
        and not _verifier_result_is_valid(verifier_result)
    ):
        return TransitionDecision(
            next_node="repair_and_resume",
            branch_kind="repair",
            reason=_MISSING_VERIFIER_REASONS[current_step_id],
        )

    if current_step_id == "run_brainstorming":
        if observation["status"] == "succeeded" and verifier_result is not None and not verifier_result["passed"]:
            return TransitionDecision(
                next_node='run_brainstorming',
                branch_kind='retry',
                reason='Brainstorming clarification and design-package readiness gates must pass before implementation planning.',
            )
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="approve_subagent_review",
            branch_kind="continue",
            reason="run_brainstorming completed; continue to approve_subagent_review",
        )

    if current_step_id == "approve_subagent_review":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('subagent_review_approved'), 'is_false', None):
                return TransitionDecision(
                    next_node='finalize_delivery_summary',
                    branch_kind='complete',
                    reason='The user declined the required subagent review pass, so the workflow must stop before implementation planning.',
                )
        return TransitionDecision(
            next_node="run_spec_review",
            branch_kind="continue",
            reason="approve_subagent_review completed; continue to run_spec_review",
        )

    if current_step_id == "run_spec_review":
        if observation["status"] == "succeeded" and verifier_result is not None and not verifier_result["passed"]:
            return TransitionDecision(
                next_node='run_spec_review',
                branch_kind='retry',
                reason='The subagent review loop must complete with concrete artifacts and readiness before implementation planning.',
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
            if condition_matches(structured_output.get('ready_for_planning'), 'is_false', None):
                return TransitionDecision(
                    next_node='run_brainstorming',
                    branch_kind='retry',
                    reason='Spec review found design gaps that must be revised in brainstorming before implementation planning can continue.',
                )
        return TransitionDecision(
            next_node="write_implementation_plan",
            branch_kind="continue",
            reason="run_spec_review completed; continue to write_implementation_plan",
        )

    if current_step_id == "write_implementation_plan":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('ready_for_implementation'), 'is_false', None):
                return TransitionDecision(
                    next_node='write_implementation_plan',
                    branch_kind='retry',
                    reason='Implementation planning is not ready yet and needs another pass.',
                )
        return TransitionDecision(
            next_node="execute_implementation",
            branch_kind="continue",
            reason="write_implementation_plan completed; continue to execute_implementation",
        )

    if current_step_id == "execute_implementation":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('plan_updates_required'), 'is_true', None):
                return TransitionDecision(
                    next_node='write_implementation_plan',
                    branch_kind='retry',
                    reason='Implementation revealed a plan or design issue that must be resolved before execution can continue.',
                )
            if condition_matches(structured_output.get('tasks_completed'), 'is_false', None):
                return TransitionDecision(
                    next_node='execute_implementation',
                    branch_kind='retry',
                    reason='Implementation reported unfinished tasks and must continue execution before release QA.',
                )
            if condition_matches(structured_output.get('verification_passed'), 'is_false', None):
                return TransitionDecision(
                    next_node='write_implementation_plan',
                    branch_kind='retry',
                    reason='Implementation verification did not pass and requires a plan/debugging update before execution can continue.',
                )
        return TransitionDecision(
            next_node="run_agentic_release_qa",
            branch_kind="continue",
            reason="execute_implementation completed; continue to run_agentic_release_qa",
        )

    if current_step_id == "run_agentic_release_qa":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('release_qa_verdict'), 'equals', 'do_not_ship'):
                return TransitionDecision(
                    next_node='execute_implementation',
                    branch_kind='retry',
                    reason='Release QA found a blocking regression or risk that must be fixed before pre-merge code review.',
                )
        return TransitionDecision(
            next_node="request_pre_merge_code_review",
            branch_kind="continue",
            reason="run_agentic_release_qa completed; continue to request_pre_merge_code_review",
        )

    if current_step_id == "request_pre_merge_code_review":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('changes_requested'), 'is_true', None):
                return TransitionDecision(
                    next_node='execute_implementation',
                    branch_kind='retry',
                    reason='Pre-merge code review requested implementation changes.',
                )
        return TransitionDecision(
            next_node="verify_completion",
            branch_kind="continue",
            reason="request_pre_merge_code_review completed; continue to verify_completion",
        )

    if current_step_id == "verify_completion":
        if observation["status"] == "succeeded" and verifier_result is not None and not verifier_result["passed"]:
            return TransitionDecision(
                next_node='execute_implementation',
                branch_kind='retry',
                reason='Final completion verification did not pass and the workflow must re-enter implementation to clear remaining issues or evidence gaps.',
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
            if condition_matches(structured_output.get('verification_passed'), 'is_false', None):
                return TransitionDecision(
                    next_node='execute_implementation',
                    branch_kind='retry',
                    reason='Final completion verification found remaining implementation or verification risks that must be resolved before the workflow can claim completion.',
                )
        return TransitionDecision(
            next_node="finalize_delivery_summary",
            branch_kind="complete",
            reason="verify_completion completed successfully",
        )

    if current_step_id == "request_unblocking_input":
        if observation["status"] == "succeeded":
            recovery_error = workflow_state.recovery_output_validation_error(
                current_step_id=current_step_id,
                structured_output=observation.get("structured_output"),
            )
            if recovery_error is not None:
                return TransitionDecision(
                    next_node="request_unblocking_input",
                    branch_kind="repair",
                    reason=recovery_error,
                )
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
            repair_attempts = int(state.get("repair_blocked_attempts") or 0)
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
            recovery_error = workflow_state.recovery_output_validation_error(
                current_step_id=current_step_id,
                structured_output=observation.get("structured_output"),
            )
            if recovery_error is not None:
                return TransitionDecision(
                    next_node="repair_and_resume",
                    branch_kind="retry",
                    reason=recovery_error,
                )
            structured_output = observation.get("structured_output") or {}
            if isinstance(structured_output, dict) and structured_output.get("needs_external_unblocking") is True:
                return TransitionDecision(
                    next_node="request_unblocking_input",
                    branch_kind="repair",
                    reason="repair explicitly requested external unblocking before the original stage can retry",
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
    if current_step_id in {"run_brainstorming", "run_spec_review"}:
        if verifier_result is not None and not _verifier_is_passed(verifier_result):
            return None
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


def _verifier_result_is_valid(verifier_result: object) -> bool:
    return isinstance(verifier_result, dict) and isinstance(
        verifier_result.get("passed"), bool
    )


def _verifier_is_passed(verifier_result: object) -> bool:
    return _verifier_result_is_valid(verifier_result) and verifier_result.get("passed") is True
