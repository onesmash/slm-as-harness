from __future__ import annotations

from workflows.common.policies import TransitionDecision


def choose_next_node(
    *,
    current_step_id: str,
    state: dict,
    observation: dict,
    verifier_result: dict | None,
) -> TransitionDecision:
    if current_step_id == "collect_context":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node="request_missing_access",
                branch_kind="repair",
                reason="host reported blocked while collecting runtime context",
            )
        if verifier_result is not None and not verifier_result["passed"]:
            return TransitionDecision(
                next_node="recheck_runtime_scaffold",
                branch_kind="repair",
                reason="verifier detected a mismatch in runtime scaffold reporting",
            )
        return TransitionDecision(
            next_node="finalize_summary",
            branch_kind="complete",
            reason="runtime scaffold status is sufficient for final summary",
        )

    if current_step_id == "request_missing_access":
        return TransitionDecision(
            next_node="finalize_summary",
            branch_kind="complete",
            reason="repair step completed and host can summarize next user action",
        )

    if current_step_id == "recheck_runtime_scaffold":
        if observation["status"] == "blocked":
            return TransitionDecision(
                next_node="request_missing_access",
                branch_kind="repair",
                reason="recheck step is blocked and needs user help",
            )
        return TransitionDecision(
            next_node="finalize_summary",
            branch_kind="complete",
            reason="recheck completed and workflow can finalize",
        )

    raise LookupError(f"no transition policy for step: {current_step_id}")
