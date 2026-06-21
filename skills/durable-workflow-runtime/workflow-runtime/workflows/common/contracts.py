from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Literal, TypedDict


VerifierKind = Literal["python_callable", "shell_command"]


@dataclass(frozen=True)
class WorkflowInputContract:
    task_input_schema: dict
    context_schema: dict
    constraints_schema: dict

    def to_start_input_schema(self) -> dict:
        return {
            "task_input": deepcopy(self.task_input_schema),
            "context": deepcopy(self.context_schema),
            "constraints": deepcopy(self.constraints_schema),
        }


@dataclass(frozen=True)
class StepVerifier:
    kind: VerifierKind
    ref: str
    timeout_seconds: int = 30
    run_on_status: list[str] = field(default_factory=lambda: ["succeeded"])


@dataclass(frozen=True)
class SkillUseWhen:
    operations: list[str] = field(default_factory=list)
    file_patterns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillRoute:
    skill: str
    use_when: SkillUseWhen
    usage_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StepContract:
    done_when: list[str]
    output_schema: dict
    failure_schema: dict
    skill_routing: list[SkillRoute] = field(default_factory=list)
    verifier: StepVerifier | None = None


class VerifierResult(TypedDict):
    passed: bool
    message: str
    details: dict


def make_verifier_result(
    *,
    passed: bool,
    message: str,
    details: dict | None = None,
) -> VerifierResult:
    return {
        "passed": bool(passed),
        "message": message,
        "details": details or {},
    }
