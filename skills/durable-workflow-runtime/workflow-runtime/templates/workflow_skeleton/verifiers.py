from __future__ import annotations

from workflows.common.contracts import VerifierResult, make_verifier_result


def verify_run_primary_stage(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    output = _output(observation)
    artifacts = output.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return _fail("artifacts must be a non-empty list", run_id, step_id, state)
    summary = output.get("handoff_summary")
    if not isinstance(summary, str) or not summary.strip():
        return _fail("handoff_summary must be a non-empty string", run_id, step_id, state)
    if output.get("ready_for_finish") is not True:
        return _fail("ready_for_finish must be true before finalization", run_id, step_id, state)
    return make_verifier_result(
        passed=True,
        message="primary stage output accepted",
        details={"repo_root": repo_root, "run_id": run_id, "step_id": step_id},
    )


def _output(observation: dict) -> dict:
    structured_output = observation.get("structured_output") or {}
    return structured_output if isinstance(structured_output, dict) else {}


def _fail(message: str, run_id: str, step_id: str, state: dict | None) -> VerifierResult:
    return make_verifier_result(
        passed=False,
        message=message,
        details={
            "run_id": run_id,
            "step_id": step_id,
            "state": state or {},
        },
    )
