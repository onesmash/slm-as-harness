from __future__ import annotations

from workflows.common.policies import TransitionDecision, condition_matches, max_steps_exceeded_decision


def choose_next_node(
    *,
    current_step_id: str,
    state: dict,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision:
    max_steps_decision = max_steps_exceeded_decision(
        current_step_id=current_step_id,
        state=state,
    )
    if max_steps_decision is not None:
        return max_steps_decision

    if current_step_id == "run_brainstorming":
        if verifier_result is not None and not verifier_result["passed"]:
            return TransitionDecision(
                next_node='run_brainstorming',
                branch_kind='retry',
                reason='Brainstorming clarification and approval gates must pass before OpenSpec formalization.',
            )
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="propose_openspec_change",
            branch_kind="continue",
            reason="run_brainstorming completed; continue to propose_openspec_change",
        )

    if current_step_id == "propose_openspec_change":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="refine_change_with_openspec",
            branch_kind="continue",
            reason="propose_openspec_change completed; continue to refine_change_with_openspec",
        )

    if current_step_id == "refine_change_with_openspec":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('ready_for_apply'), 'is_false', None):
                return TransitionDecision(
                    next_node='refine_change_with_openspec',
                    branch_kind='retry',
                    reason='OpenSpec refinement is not ready for implementation yet.',
                )
        return TransitionDecision(
            next_node="approve_refine",
            branch_kind="continue",
            reason="refine_change_with_openspec completed; continue to approve_refine",
        )

    if current_step_id == "approve_refine":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('user_approved'), 'is_true', None):
                return TransitionDecision(
                    next_node='execute_implementation',
                    branch_kind='continue',
                    reason='User approved refinement; proceeding to implementation.',
                )
            if condition_matches(structured_output.get('additional_refinement_needed'), 'is_true', None):
                return TransitionDecision(
                    next_node='refine_change_with_openspec',
                    branch_kind='retry',
                    reason='User requested additional refinement before implementation.',
                )
        return TransitionDecision(
            next_node="execute_implementation",
            branch_kind="continue",
            reason="approve_refine completed; continue to execute_implementation",
        )

    if current_step_id == "execute_implementation":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
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
            if condition_matches(structured_output.get('release_qa_verdict'), 'equals', 'blocked'):
                return TransitionDecision(
                    next_node='request_unblocking_input',
                    branch_kind='repair',
                    reason='Release QA was blocked and needs missing QA environment, artifact, credential, device, or baseline input.',
                )
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('release_qa_verdict'), 'equals', 'do_not_ship'):
                return TransitionDecision(
                    next_node='execute_implementation',
                    branch_kind='retry',
                    reason='Release QA found a blocking regression or risk that must be fixed before final review.',
                )
        return TransitionDecision(
            next_node="request_final_code_review",
            branch_kind="continue",
            reason="run_agentic_release_qa completed; continue to request_final_code_review",
        )

    if current_step_id == "request_final_code_review":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('review_status'), 'equals', 'blocked'):
                return TransitionDecision(
                    next_node='request_unblocking_input',
                    branch_kind='repair',
                    reason='Merged-final review reported a blocked status and needs the missing review input.',
                )
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('changes_requested'), 'is_true', None):
                return TransitionDecision(
                    next_node='execute_implementation',
                    branch_kind='retry',
                    reason='Merged-final review requested implementation changes.',
                )
        return TransitionDecision(
            next_node="write_code_kb_feedback",
            branch_kind="continue",
            reason="request_final_code_review completed; continue to write_code_kb_feedback",
        )

    if current_step_id == "write_code_kb_feedback":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="finalize_delivery_summary",
            branch_kind="complete",
            reason="write_code_kb_feedback completed successfully",
        )

    if current_step_id == "request_unblocking_input":
        if observation["status"] == "succeeded":
            return_stage_id = state.get("return_stage_id")
            if not return_stage_id:
                return TransitionDecision(
                    next_node="request_unblocking_input",
                    branch_kind="repair",
                    reason="cannot resume because return_stage_id is missing",
                )
            return TransitionDecision(
                next_node=return_stage_id,
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
