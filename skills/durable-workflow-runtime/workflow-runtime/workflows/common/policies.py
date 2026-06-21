from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


BranchKind = Literal[
    "continue",
    "retry",
    "repair",
    "complete",
    "blocked_terminal",
    "failed_terminal",
]


@dataclass(frozen=True)
class TransitionDecision:
    next_node: str
    branch_kind: BranchKind
    reason: str
    metadata: dict = field(default_factory=dict)

    def to_trace_payload(self, *, next_node: str | None = None) -> dict:
        return {
            "next_node": next_node or self.next_node,
            "branch_kind": self.branch_kind,
            "reason": self.reason,
            **self.metadata,
        }


def condition_matches(actual, operator: str, expected) -> bool:
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator == "is_true":
        return actual is True
    if operator == "is_false":
        return actual is False
    if operator == "truthy":
        return bool(actual)
    if operator == "falsey":
        return not bool(actual)
    if operator == "missing":
        return actual is None
    if operator == "non_empty":
        return bool(actual)
    if operator == "empty":
        return not bool(actual)
    return False


def max_steps_exceeded_decision(
    *,
    current_step_id: str,
    state: dict,
) -> TransitionDecision | None:
    if current_step_id in {"request_unblocking_input", "repair_and_resume"}:
        return None

    constraints = state.get("constraints") or {}
    if not isinstance(constraints, dict):
        return None

    max_steps = constraints.get("max_steps")
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
        return None

    attempt_counts = state.get("attempt_counts") or {}
    if not isinstance(attempt_counts, dict):
        return None

    total_attempts = sum(
        count
        for count in attempt_counts.values()
        if isinstance(count, int) and not isinstance(count, bool) and count > 0
    )
    if total_attempts < max_steps:
        return None

    return TransitionDecision(
        next_node="request_unblocking_input",
        branch_kind="repair",
        reason=f"workflow reached max_steps={max_steps} after {total_attempts} observed step(s)",
        metadata={"max_steps": max_steps, "attempt_count": total_attempts},
    )
