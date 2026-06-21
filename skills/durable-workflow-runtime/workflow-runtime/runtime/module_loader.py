from __future__ import annotations

import importlib

from runtime.errors import WorkflowExecutionError


def load_workflow_modules(workflow_id: str) -> dict:
    try:
        return {
            "contract": importlib.import_module(f"workflows.{workflow_id}.contract"),
            "graphbuilder_runtime": importlib.import_module(
                f"workflows.{workflow_id}.graphbuilder_runtime"
            ),
            "policy": importlib.import_module(f"workflows.{workflow_id}.policy"),
            "state": importlib.import_module(f"workflows.{workflow_id}.state"),
        }
    except Exception as exc:
        raise WorkflowExecutionError(f"failed to load workflow {workflow_id}: {exc}") from exc
