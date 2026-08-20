from __future__ import annotations

from workflows.common.policies import (
    TransitionDecision,
    condition_matches,
    max_steps_exceeded_decision,
)

REQUIRED_VERIFIER_STAGE_IDS = ('collect_earnings_packet',
 'analyze_earnings_call',
 'update_coverage_model',
 'audit_coverage_model',
 'draft_earnings_note')
MISSING_VERIFIER_ROUTES = {'collect_earnings_packet': {'next_node': 'repair_and_resume',
                             'branch_kind': 'repair',
                             'reason': 'collect_earnings_packet completed without a valid verifier '
                                       'result; fail closed before continuing.'},
 'analyze_earnings_call': {'next_node': 'repair_and_resume',
                           'branch_kind': 'repair',
                           'reason': 'analyze_earnings_call completed without a valid verifier '
                                     'result; fail closed before continuing.'},
 'update_coverage_model': {'next_node': 'repair_and_resume',
                           'branch_kind': 'repair',
                           'reason': 'update_coverage_model completed without a valid verifier '
                                     'result; fail closed before continuing.'},
 'audit_coverage_model': {'next_node': 'repair_model_audit',
                          'branch_kind': 'repair',
                          'reason': 'coverage-model audit is fail-closed without a passing '
                                    'verifier'},
 'draft_earnings_note': {'next_node': 'repair_and_resume',
                         'branch_kind': 'repair',
                         'reason': 'draft_earnings_note completed without a valid verifier result; '
                                   'fail closed before continuing.'}}

_RECOVERY_OUTPUT_SCHEMAS = {'repair_model_audit': {'repair_summary': 'string', 'repair_actions': 'string[]'},
 'request_unblocking_input': {'blocking_reason': 'string',
                              'user_action_needed': 'string',
                              'suggested_next_input': 'string?'},
 'repair_and_resume': {'retry_reason': 'string',
                       'retry_notes': 'string',
                       'repair_actions': 'string[]'}}


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
            next_node='finalize_earnings_review',
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

    if current_step_id == "collect_earnings_packet":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('packet_ready'), 'is_false', None):
                return TransitionDecision(
                    next_node='collect_earnings_packet',
                    branch_kind='retry',
                    reason='earnings packet is still incomplete and needs another intake pass',
                )
        return TransitionDecision(
            next_node="analyze_earnings_call",
            branch_kind="continue",
            reason="collect_earnings_packet completed; continue to analyze_earnings_call",
        )

    if current_step_id == "analyze_earnings_call":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        structured_output = observation.get("structured_output") or {}
        if isinstance(structured_output, dict):
            if condition_matches(structured_output.get('call_analysis_ready'), 'is_false', None):
                return TransitionDecision(
                    next_node='analyze_earnings_call',
                    branch_kind='retry',
                    reason='call analysis is incomplete and needs another pass',
                )
        return TransitionDecision(
            next_node="update_coverage_model",
            branch_kind="continue",
            reason="analyze_earnings_call completed; continue to update_coverage_model",
        )

    if current_step_id == "update_coverage_model":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="audit_coverage_model",
            branch_kind="continue",
            reason="update_coverage_model completed; continue to audit_coverage_model",
        )

    if current_step_id == "audit_coverage_model":
        if observation["status"] == "succeeded" and _verifier_result_is_valid(verifier_result) and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node='repair_model_audit',
                branch_kind='repair',
                reason='coverage-model audit verifier failed; route to model-audit repair',
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
            if condition_matches(structured_output.get('skip_note'), 'is_true', None):
                return TransitionDecision(
                    next_node='finalize_earnings_review',
                    branch_kind='complete',
                    reason='analyst requested model-only update; skip the earnings note and stage artifacts for sign-off',
                )
        return TransitionDecision(
            next_node="draft_earnings_note",
            branch_kind="continue",
            reason="audit_coverage_model completed; continue to draft_earnings_note",
        )

    if current_step_id == "repair_model_audit":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node="repair_and_resume",
                branch_kind="repair",
                reason="repair_model_audit is blocked and should be triaged by shared repair first",
            )
        if verifier_result is not None and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node="repair_model_audit",
                branch_kind="retry",
                reason="repair_model_audit repair output did not satisfy verifier checks",
            )
        if observation["status"] in ('partial', 'failed'):
            return TransitionDecision(
                next_node="repair_model_audit",
                branch_kind="retry",
                reason="repair_model_audit recovery stage still needs more iteration",
            )
        if observation["status"] == "succeeded":
            recovery_error = recovery_output_validation_error(
                current_step_id="repair_model_audit",
                structured_output=observation.get("structured_output"),
            )
            if recovery_error is not None:
                return TransitionDecision(
                    next_node="repair_model_audit",
                    branch_kind="retry",
                    reason=recovery_error,
                )
            return TransitionDecision(
                next_node="audit_coverage_model",
                branch_kind="continue",
                reason="repair_model_audit completed recovery work; return to audit_coverage_model",
            )
        return TransitionDecision(
            next_node="repair_model_audit",
            branch_kind="retry",
            reason="repair_model_audit recovery stage returned an unresolved status",
        )

    if current_step_id == "draft_earnings_note":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="finalize_earnings_review",
            branch_kind="complete",
            reason="draft_earnings_note completed successfully",
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
