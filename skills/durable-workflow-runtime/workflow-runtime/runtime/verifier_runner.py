from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

from runtime.errors import WorkflowExecutionError


def run_step_verifier(*, repo_root: str | Path, modules: dict, verifier, run_state, observation):
    if verifier is None:
        return None
    if observation.status not in verifier.run_on_status:
        return None
    repo_path = Path(repo_root).resolve()
    if verifier.kind == "shell_command":
        completed = subprocess.run(
            verifier.ref,
            cwd=repo_path,
            shell=True,
            capture_output=True,
            text=True,
            timeout=verifier.timeout_seconds,
            check=False,
        )
        return {
            "passed": completed.returncode == 0,
            "message": (
                "shell verifier passed"
                if completed.returncode == 0
                else "shell verifier failed"
            ),
            "details": {
                "command": verifier.ref,
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            },
        }
    if verifier.kind != "python_callable":
        raise WorkflowExecutionError(f"unsupported verifier kind: {verifier.kind}")
    module_name, function_name = verifier.ref.split(":", 1)
    try:
        module = importlib.import_module(module_name)
        verifier_fn = getattr(module, function_name)
    except Exception as exc:
        raise WorkflowExecutionError(f"failed to load verifier {verifier.ref}: {exc}") from exc
    try:
        return verifier_fn(
            repo_root=str(repo_path),
            run_id=run_state.run_id,
            step_id=observation.step_id,
            observation=observation.to_dict(),
            state=run_state.graph_state if isinstance(run_state.graph_state, dict) else None,
        )
    except Exception as exc:
        raise WorkflowExecutionError(f"verifier execution failed: {exc}") from exc
