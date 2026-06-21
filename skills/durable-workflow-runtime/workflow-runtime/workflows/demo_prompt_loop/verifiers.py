from __future__ import annotations

from pathlib import Path

from workflows.common.contracts import VerifierResult, make_verifier_result

SKILL_RUNTIME_ROOT = Path(__file__).resolve().parents[2]


def verify_runtime_scaffold(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    del repo_root
    runtime_dir = SKILL_RUNTIME_ROOT
    reported = observation.get("structured_output") or {}
    reported_exists = bool(reported.get("runtime_exists"))
    actual_exists = runtime_dir.exists()
    if reported_exists != actual_exists:
        return make_verifier_result(
            passed=False,
            message="reported runtime existence does not match filesystem",
            details={
                "run_id": run_id,
                "step_id": step_id,
                "reported_exists": reported_exists,
                "actual_exists": actual_exists,
            },
        )

    reported_entries = sorted(reported.get("top_level_entries") or [])
    actual_entries = sorted(
        path.name
        for path in runtime_dir.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    ) if actual_exists else []
    if reported_exists and reported_entries != actual_entries:
        return make_verifier_result(
            passed=False,
            message="reported runtime entries do not match filesystem",
            details={
                "reported_entries": reported_entries,
                "actual_entries": actual_entries,
                "state": state or {},
            },
        )

    return make_verifier_result(
        passed=True,
        message="runtime scaffold check passed",
        details={"run_id": run_id, "step_id": step_id},
    )
