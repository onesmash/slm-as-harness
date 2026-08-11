from __future__ import annotations

from workflows.common.policies import (
    TransitionDecision,
    condition_matches,
    max_steps_exceeded_decision,
)

REQUIRED_VERIFIER_STAGE_IDS = ('run_brainstorming',
 'approve_subagent_review',
 'run_spec_review',
 'write_implementation_plan',
 'execute_implementation',
 'run_agentic_release_qa',
 'request_pre_merge_code_review',
 'verify_completion')
MISSING_VERIFIER_ROUTES = {'run_brainstorming': {'next_node': 'repair_and_resume',
                       'branch_kind': 'repair',
                       'reason': 'run_brainstorming completed without a valid verifier result; '
                                 'fail closed before continuing.'},
 'approve_subagent_review': {'next_node': 'repair_and_resume',
                             'branch_kind': 'repair',
                             'reason': 'approve_subagent_review completed without a valid verifier '
                                       'result; fail closed before continuing.'},
 'run_spec_review': {'next_node': 'repair_and_resume',
                     'branch_kind': 'repair',
                     'reason': 'run_spec_review completed without a valid verifier result; fail '
                               'closed before continuing.'},
 'write_implementation_plan': {'next_node': 'repair_and_resume',
                               'branch_kind': 'repair',
                               'reason': 'write_implementation_plan completed without a valid '
                                         'verifier result; fail closed before continuing.'},
 'execute_implementation': {'next_node': 'repair_and_resume',
                            'branch_kind': 'repair',
                            'reason': 'execute_implementation completed without a valid verifier '
                                      'result; fail closed before continuing.'},
 'run_agentic_release_qa': {'next_node': 'repair_and_resume',
                            'branch_kind': 'repair',
                            'reason': 'run_agentic_release_qa completed without a valid verifier '
                                      'result; fail closed before continuing.'},
 'request_pre_merge_code_review': {'next_node': 'repair_and_resume',
                                   'branch_kind': 'repair',
                                   'reason': 'request_pre_merge_code_review completed without a '
                                             'valid verifier result; fail closed before '
                                             'continuing.'},
 'verify_completion': {'next_node': 'repair_and_resume',
                       'branch_kind': 'repair',
                       'reason': 'verify_completion completed without a valid verifier result; '
                                 'fail closed before continuing.'}}

_RECOVERY_OUTPUT_SCHEMAS = {'request_unblocking_input': {'blocking_reason': 'string',
                              'user_action_needed': 'string',
                              'suggested_next_input': 'string?'},
 'repair_and_resume': {'retry_reason': 'string',
                       'retry_notes': 'string',
                       'repair_actions': 'string[]',
                       'needs_external_unblocking': 'boolean?'}}


def recovery_output_validation_error(*, current_step_id: str, structured_output: object) -> str | None:
    schema = _RECOVERY_OUTPUT_SCHEMAS.get(current_step_id)
    if schema is None:
        return None
    if not isinstance(structured_output, dict):
        return "recovery succeeded output must be an object"
    unexpected = sorted(repr(key) for key in structured_output if key not in schema)
    if unexpected:
        return f"{current_step_id} returned unexpected fields: {unexpected}"
    missing = [
        key
        for key, schema_type in schema.items()
        if not schema_type.endswith("?") and key not in structured_output
    ]
    if missing:
        return f"{current_step_id} is missing required fields: {missing}"
    for key, schema_type in schema.items():
        if key not in structured_output:
            continue
        message = _recovery_schema_type_error(
            key,
            structured_output[key],
            schema_type.rstrip("?"),
        )
        if message:
            return message
    if current_step_id == "repair_and_resume":
        actions = structured_output.get("repair_actions")
        if not isinstance(actions, list) or not actions or any(
            not isinstance(item, str) or not item.strip() for item in actions
        ):
            return "repair_actions must contain at least one meaningful action"
    return None


def _recovery_schema_type_error(key: str, value: object, schema_type: str) -> str | None:
    if schema_type == "string":
        if not isinstance(value, str):
            return f"{key} must be a string"
        if not value.strip():
            return f"{key} must be meaningful text"
        return None
    if schema_type == "boolean":
        return None if isinstance(value, bool) else f"{key} must be a boolean"
    if schema_type == "integer":
        return None if isinstance(value, int) and not isinstance(value, bool) else f"{key} must be an integer"
    if schema_type == "number":
        return None if isinstance(value, (int, float)) and not isinstance(value, bool) else f"{key} must be a number"
    if schema_type == "object":
        return None if isinstance(value, dict) else f"{key} must be an object"
    if schema_type.endswith("[]"):
        if not isinstance(value, list):
            return f"{key} must be a list"
        item_type = schema_type[:-2]
        for index, item in enumerate(value):
            message = _recovery_schema_type_error(f"{key}[{index}]", item, item_type)
            if message:
                return message
        return None
    return f"{key} uses unsupported recovery schema type: {schema_type}"


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
        include_repair_stages=True,
    )
    if budget_decision is not None:
        return TransitionDecision(
            next_node='finalize_delivery_summary',
            branch_kind="complete",
            reason=f"{budget_decision.reason}; terminate with a degraded final summary",
            metadata={
                **budget_decision.metadata,
                "degraded": True,
                "terminal_reason": "max_steps_exceeded",
            },
        )

    if (
        current_step_id in REQUIRED_VERIFIER_STAGE_IDS
        and observation.get("status") == "succeeded"
        and not _verifier_result_is_valid(verifier_result)
    ):
        route = MISSING_VERIFIER_ROUTES[current_step_id]
        return TransitionDecision(
            next_node=route["next_node"],
            branch_kind=route["branch_kind"],
            reason=route["reason"],
        )

    if current_step_id == "run_brainstorming":
        if observation["status"] == "succeeded" and _verifier_result_is_valid(verifier_result) and not _verifier_is_passed(verifier_result):
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
        if observation["status"] == "succeeded" and _verifier_result_is_valid(verifier_result) and not _verifier_is_passed(verifier_result):
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
        if observation["status"] == "succeeded" and _verifier_result_is_valid(verifier_result) and not _verifier_is_passed(verifier_result):
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
            recovery_error = recovery_output_validation_error(
                current_step_id="request_unblocking_input",
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
                next_node='request_unblocking_input',
                branch_kind='repair',
                reason='repair exhausted self-repair attempts and now requires external help before retry',
            )
        if observation["status"] == "succeeded":
            recovery_error = recovery_output_validation_error(
                current_step_id="repair_and_resume",
                structured_output=observation.get("structured_output"),
            )
            if recovery_error is not None:
                return TransitionDecision(
                    next_node="repair_and_resume",
                    branch_kind="retry",
                    reason=recovery_error,
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
    return _verifier_result_is_valid(verifier_result) and verifier_result.get("passed") is True


def _verifier_result_is_valid(verifier_result: object) -> bool:
    return isinstance(verifier_result, dict) and isinstance(verifier_result.get("passed"), bool)
