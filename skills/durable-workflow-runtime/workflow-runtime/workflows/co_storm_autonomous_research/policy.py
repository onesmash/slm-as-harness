from __future__ import annotations

from workflows.common.policies import (
    TransitionDecision,
    condition_matches,
    max_steps_exceeded_decision,
)

REQUIRED_VERIFIER_STAGE_IDS = ('warm_start_shared_space',
 'launch_expert_subagents',
 'autonomous_roundtable',
 'reorganize_knowledge_space',
 'synthesize_report',
 'verify_report')
MISSING_VERIFIER_ROUTES = {'warm_start_shared_space': {'next_node': 'repair_and_resume',
                             'branch_kind': 'repair',
                             'reason': 'warm_start_shared_space completed without a valid verifier '
                                       'result; fail closed before continuing.'},
 'launch_expert_subagents': {'next_node': 'repair_and_resume',
                             'branch_kind': 'repair',
                             'reason': 'launch_expert_subagents completed without a verifier '
                                       'result; fail closed before Moderator synthesis.'},
 'autonomous_roundtable': {'next_node': 'repair_and_resume',
                           'branch_kind': 'repair',
                           'reason': 'autonomous_roundtable completed without a valid verifier '
                                     'result; fail closed before continuing.'},
 'reorganize_knowledge_space': {'next_node': 'repair_and_resume',
                                'branch_kind': 'repair',
                                'reason': 'reorganize_knowledge_space completed without a valid '
                                          'verifier result; fail closed before continuing.'},
 'synthesize_report': {'next_node': 'repair_and_resume',
                       'branch_kind': 'repair',
                       'reason': 'synthesize_report completed without a verifier result; fail '
                                 'closed and preserve the report for recovery.'},
 'verify_report': {'next_node': 'repair_and_resume',
                   'branch_kind': 'repair',
                   'reason': 'verify_report completed without a verifier result; fail closed and '
                             'preserve the report for recovery.'}}

_RECOVERY_OUTPUT_SCHEMAS = {'repair_report': {'report_repair_summary': 'string',
                   'repair_actions': 'string[]',
                   'repair_ready': 'boolean'},
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
            next_node='finalize_collaborative_report',
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

    if current_step_id == "warm_start_shared_space":
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
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
                    reason='Moderator determined that semantic coverage is complete or the autonomous budget requires an explicitly partial report.',
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
        if observation["status"] == "succeeded" and _verifier_result_is_valid(verifier_result) and not _verifier_is_passed(verifier_result):
            return TransitionDecision(
                next_node='repair_report',
                branch_kind='repair',
                reason='Report synthesis failed the in-place locator or report-file gate; use report-specific repair before re-synthesis.',
            )
        status_decision = _route_common_failure(
            current_step_id=current_step_id,
            observation=observation,
            verifier_result=verifier_result,
        )
        if status_decision is not None:
            return status_decision
        return TransitionDecision(
            next_node="verify_report",
            branch_kind="continue",
            reason="synthesize_report completed; continue to verify_report",
        )

    if current_step_id == "verify_report":
        if observation["status"] == "succeeded" and _verifier_result_is_valid(verifier_result) and not _verifier_is_passed(verifier_result):
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
            recovery_error = recovery_output_validation_error(
                current_step_id="repair_report",
                structured_output=observation.get("structured_output"),
            )
            if recovery_error is not None:
                return TransitionDecision(
                    next_node="repair_report",
                    branch_kind="retry",
                    reason=recovery_error,
                )
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
                next_node='finalize_collaborative_report',
                branch_kind='partial',
                reason='repair exhausted 3 self-repair attempts; terminate with a partial handoff instead of waiting for user input',
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
