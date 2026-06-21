from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class DemoGraphState:
    attempt_counts: dict[str, int] = field(default_factory=dict)
    original_goal: str | None = None
    max_steps: int | None = None


def make_initial_state(request: dict) -> DemoGraphState:
    constraints = request.get("constraints") or {}
    task_input = request.get("task_input") or {}
    return DemoGraphState(
        attempt_counts={},
        original_goal=task_input.get("goal"),
        max_steps=constraints.get("max_steps"),
    )


def serialize_state(state: DemoGraphState) -> dict:
    return asdict(state)


def deserialize_state(payload: dict | None) -> DemoGraphState:
    payload = payload or {}
    return DemoGraphState(
        attempt_counts=dict(payload.get("attempt_counts") or {}),
        original_goal=payload.get("original_goal"),
        max_steps=payload.get("max_steps"),
    )
