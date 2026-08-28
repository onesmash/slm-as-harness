from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


DELETE_SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_SKILL_ROOT = DELETE_SKILL_ROOT.parent
_SAFE_WORKFLOW_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
RUNTIME_SCRIPTS_ROOT = DEFAULT_RUNTIME_SKILL_ROOT / "scripts"

if str(RUNTIME_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SCRIPTS_ROOT))

from workflow_shortcut_skill import delete_workflow_shortcut_skill


class DeleteWorkflowError(ValueError):
    pass


def delete_workflow(
    *,
    runtime_skill_root: str | Path,
    workflow_id: str,
    confirm: str,
    new_default_workflow_id: str | None = None,
    clear_default: bool = False,
) -> dict[str, Any]:
    runtime_root = _resolve_runtime_skill_root(runtime_skill_root)
    resolved_workflow_id = _validate_workflow_id(workflow_id)
    _validate_confirmation(resolved_workflow_id, confirm)
    binding_path = runtime_root / "workflow-binding.json"
    workflows_root = runtime_root / "workflow-runtime" / "workflows"
    workflow_dir = workflows_root / resolved_workflow_id.replace("-", "_")

    binding_payload = _load_json_object(binding_path, "workflow binding config")
    workflows = _get_workflows(binding_payload)
    binding_index = _find_binding_index(workflows, resolved_workflow_id)
    if binding_index is None:
        raise DeleteWorkflowError(
            f"workflow is not published in binding catalog: {resolved_workflow_id}"
        )
    if not workflow_dir.is_dir():
        raise DeleteWorkflowError(f"configured workflow does not exist: {resolved_workflow_id}")

    _update_default_workflow(
        binding_payload=binding_payload,
        workflows=workflows,
        workflow_id=resolved_workflow_id,
        new_default_workflow_id=new_default_workflow_id,
        clear_default=clear_default,
    )

    removed_entry = workflows.pop(binding_index)
    backup_dir = workflows_root / f".{resolved_workflow_id}.delete-backup"
    _remove_path(backup_dir)

    try:
        workflow_dir.replace(backup_dir)
        _write_json_atomic(binding_path, binding_payload)
        shortcut_payload = delete_workflow_shortcut_skill(
            runtime_skill_root=runtime_root,
            workflow_id=resolved_workflow_id,
        )
        _remove_path(backup_dir)
    except Exception:
        if not workflow_dir.exists() and backup_dir.exists():
            backup_dir.replace(workflow_dir)
        workflows.insert(binding_index, removed_entry)
        raise

    return {
        "kind": "workflow_deletion",
        "workflow_id": resolved_workflow_id,
        "workflow_dir": str(workflow_dir),
        "binding_file": str(binding_path),
        "removed_binding": True,
        "removed_workflow_dir": True,
        "default_workflow_id": binding_payload.get("default_workflow_id"),
        **shortcut_payload,
    }


def _resolve_runtime_skill_root(runtime_skill_root: str | Path) -> Path:
    path = Path(runtime_skill_root).expanduser().resolve()
    required_paths = [
        path / "workflow-binding.json",
        path / "workflow-runtime",
        path / "workflow-runtime" / "workflows",
    ]
    missing = [str(item) for item in required_paths if not item.exists()]
    if missing:
        raise DeleteWorkflowError(
            f"missing durable-workflow-runtime paths: {', '.join(missing)}"
        )
    return path


def _validate_workflow_id(value: object) -> str:
    if not isinstance(value, str):
        raise DeleteWorkflowError("workflow_id must be a string")
    workflow_id = value.strip()
    if not workflow_id or not _SAFE_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise DeleteWorkflowError(
            "workflow_id must contain only letters, numbers, dot, dash, or underscore"
        )
    if workflow_id in {".", ".."}:
        raise DeleteWorkflowError("workflow_id must not be a path traversal segment")
    return workflow_id


def _validate_confirmation(workflow_id: str, confirm: str) -> None:
    if confirm != workflow_id:
        raise DeleteWorkflowError("--confirm must exactly match --workflow-id")


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeleteWorkflowError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DeleteWorkflowError(f"{label} must be a JSON object")
    return payload


def _get_workflows(binding_payload: dict[str, Any]) -> list[dict[str, Any]]:
    workflows = binding_payload.get("workflows")
    if not isinstance(workflows, list):
        raise DeleteWorkflowError("workflow binding config field 'workflows' must be a list")
    if not all(isinstance(item, dict) for item in workflows):
        raise DeleteWorkflowError("workflow binding config workflows entries must be objects")
    return workflows


def _find_binding_index(workflows: list[dict[str, Any]], workflow_id: str) -> int | None:
    for index, item in enumerate(workflows):
        item_workflow_id = item.get("workflow_id")
        if isinstance(item_workflow_id, str) and item_workflow_id.strip() == workflow_id:
            return index
    return None


def _update_default_workflow(
    *,
    binding_payload: dict[str, Any],
    workflows: list[dict[str, Any]],
    workflow_id: str,
    new_default_workflow_id: str | None,
    clear_default: bool,
) -> None:
    if new_default_workflow_id and clear_default:
        raise DeleteWorkflowError(
            "choose either --new-default-workflow-id or --clear-default, not both"
        )

    current_default = binding_payload.get("default_workflow_id")
    if current_default != workflow_id:
        if new_default_workflow_id or clear_default:
            raise DeleteWorkflowError(
                "default update options are only allowed when deleting the current default workflow"
            )
        return

    if clear_default:
        binding_payload.pop("default_workflow_id", None)
        return

    if not new_default_workflow_id:
        raise DeleteWorkflowError(
            "workflow is the current default; pass --new-default-workflow-id or --clear-default"
        )

    resolved_new_default = _validate_workflow_id(new_default_workflow_id)
    if resolved_new_default == workflow_id:
        raise DeleteWorkflowError("new default workflow must be different from deleted workflow")
    if _find_binding_index(workflows, resolved_new_default) is None:
        raise DeleteWorkflowError(
            f"new default workflow is not published in binding catalog: {resolved_new_default}"
        )
    binding_payload["default_workflow_id"] = resolved_new_default


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    if path.exists():
        shutil.rmtree(path)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = delete_workflow(
            runtime_skill_root=args.runtime_skill_root,
            workflow_id=args.workflow_id,
            confirm=args.confirm,
            new_default_workflow_id=args.new_default_workflow_id,
            clear_default=args.clear_default,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Delete a workflow from durable-workflow-runtime"
    )
    parser.add_argument("--runtime-skill-root", default=str(DEFAULT_RUNTIME_SKILL_ROOT))
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--new-default-workflow-id")
    parser.add_argument("--clear-default", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
