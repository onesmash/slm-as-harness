from __future__ import annotations

import hashlib
import importlib
import sys
import threading
from pathlib import Path

from runtime.errors import WorkflowExecutionError
from runtime.workflow_identity import is_valid_workflow_id, workflow_module_name


_WORKFLOW_SOURCE_MAX_BYTES = 8 * 1024 * 1024
_MODULE_CACHE: dict[str, tuple[str, dict]] = {}
_MODULE_CACHE_LOCK = threading.RLock()


def _workflow_source_fingerprint(workflow_id: str) -> str:
    module_name = workflow_module_name(workflow_id)
    workflow_dir = (Path(__file__).resolve().parents[1] / "workflows" / module_name).resolve()
    digest = hashlib.sha256(workflow_id.encode("utf-8"))
    if not workflow_dir.is_dir():
        digest.update(b"missing")
        return digest.hexdigest()
    for path in sorted(workflow_dir.rglob("*")):
        if not path.is_file() or path.is_symlink() or "__pycache__" in path.parts:
            continue
        if path.name in {".workflow-lock.json", ".preflight-cache.json"}:
            continue
        try:
            relative = path.relative_to(workflow_dir).as_posix()
            file_size = path.stat().st_size
            digest.update(relative.encode("utf-8"))
            digest.update(str(file_size).encode("ascii"))
            if file_size <= _WORKFLOW_SOURCE_MAX_BYTES:
                digest.update(path.read_bytes())
        except (OSError, ValueError):
            digest.update(b"unreadable")
    return digest.hexdigest()


def _reload_workflow_modules(workflow_id: str) -> None:
    module_name = workflow_module_name(workflow_id)
    prefix = f"workflows.{module_name}"
    for module_name_in_sys in list(sys.modules):
        if module_name_in_sys == prefix or module_name_in_sys.startswith(f"{prefix}."):
            del sys.modules[module_name_in_sys]


def load_workflow_modules(workflow_id: str) -> dict:
    if not is_valid_workflow_id(workflow_id):
        raise WorkflowExecutionError("invalid workflow_id for module loading")
    module_name = workflow_module_name(workflow_id)
    with _MODULE_CACHE_LOCK:
        source_fingerprint = _workflow_source_fingerprint(workflow_id)
        cached = _MODULE_CACHE.get(workflow_id)
        if cached is not None and cached[0] == source_fingerprint:
            return cached[1]
        if cached is not None:
            _reload_workflow_modules(workflow_id)
        importlib.invalidate_caches()
        try:
            modules = {
                "contract": importlib.import_module(f"workflows.{module_name}.contract"),
                "graphbuilder_runtime": importlib.import_module(
                    f"workflows.{module_name}.graphbuilder_runtime"
                ),
                "policy": importlib.import_module(f"workflows.{module_name}.policy"),
                "state": importlib.import_module(f"workflows.{module_name}.state"),
            }
        except Exception as exc:
            raise WorkflowExecutionError(f"failed to load workflow {workflow_id}: {exc}") from exc
        _MODULE_CACHE[workflow_id] = (source_fingerprint, modules)
        return modules
