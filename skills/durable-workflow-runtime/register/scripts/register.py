from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any


REGISTER_SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_SKILL_ROOT = REGISTER_SKILL_ROOT.parent
_SAFE_WORKFLOW_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
RUNTIME_SCRIPTS_ROOT = DEFAULT_RUNTIME_SKILL_ROOT / "scripts"

if str(RUNTIME_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SCRIPTS_ROOT))

from workflow_shortcut_skill import ensure_workflow_shortcut_skill


class RegisterError(ValueError):
    pass


def register_flow_package(
    *,
    runtime_skill_root: str | Path,
    flow_file: str | Path,
    force: bool = False,
) -> dict[str, Any]:
    runtime_root = _resolve_runtime_skill_root(runtime_skill_root)
    flow_path = _resolve_flow_file(flow_file)
    binding_path = runtime_root / "workflow-binding.json"
    workflows_root = runtime_root / "workflow-runtime" / "workflows"

    package = _read_flow_package(flow_path)
    workflow_id = package["workflow_id"]
    target_workflow_dir = workflows_root / workflow_id
    binding_payload = _load_json_object(binding_path, "workflow binding config")
    existing_binding_index = _find_binding_index(binding_payload, workflow_id)
    target_exists = target_workflow_dir.exists()

    if (target_exists or existing_binding_index is not None) and not force:
        raise RegisterError(
            f"workflow already exists; pass --force to replace: {workflow_id}"
        )

    temp_workflow_dir = workflows_root / f".{workflow_id}.register-tmp"
    backup_workflow_dir = workflows_root / f".{workflow_id}.register-backup"
    _remove_path(temp_workflow_dir)
    _remove_path(backup_workflow_dir)

    installed_files = _extract_workflow(package["archive"], temp_workflow_dir)
    replaced_existing = target_exists or existing_binding_index is not None

    try:
        if target_exists:
            target_workflow_dir.replace(backup_workflow_dir)
        temp_workflow_dir.replace(target_workflow_dir)
        _register_binding_entry(
            binding_path=binding_path,
            binding_payload=binding_payload,
            binding_entry=package["binding_entry"],
            existing_index=existing_binding_index,
        )
        shortcut_payload = ensure_workflow_shortcut_skill(
            runtime_skill_root=runtime_root,
            workflow_id=workflow_id,
        )
        _remove_path(backup_workflow_dir)
    except Exception:
        _remove_path(target_workflow_dir)
        if backup_workflow_dir.exists():
            backup_workflow_dir.replace(target_workflow_dir)
        raise
    finally:
        _remove_path(temp_workflow_dir)
        package["archive"].close()

    return {
        "kind": "flow_registration",
        "workflow_id": workflow_id,
        "workflow_dir": str(target_workflow_dir),
        "binding_file": str(binding_path),
        "replaced_existing": replaced_existing,
        "installed_files": installed_files,
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
        raise RegisterError(f"missing durable-workflow-runtime paths: {', '.join(missing)}")
    return path


def _resolve_flow_file(flow_file: str | Path) -> Path:
    path = Path(flow_file).expanduser().resolve()
    if path.suffix != ".flow":
        raise RegisterError("flow file must use the .flow extension")
    if not path.is_file():
        raise RegisterError(f"flow file does not exist: {path}")
    return path


def _read_flow_package(flow_path: Path) -> dict[str, Any]:
    try:
        archive = zipfile.ZipFile(flow_path)
    except zipfile.BadZipFile as exc:
        raise RegisterError(f"invalid .flow archive: {flow_path}") from exc

    try:
        _validate_archive_names(archive)
        package_manifest = _read_archive_json(archive, "package-manifest.json")
        binding_entry = _read_archive_json(archive, "binding-entry.json")
        workflow_manifest = _read_archive_json(archive, "workflow/manifest.json")

        if package_manifest.get("package_type") != "durable-workflow-runtime.flow":
            raise RegisterError("package-manifest.json package_type is not durable-workflow-runtime.flow")
        workflow_id = _validate_workflow_id(package_manifest.get("workflow_id"))
        if binding_entry.get("workflow_id") != workflow_id:
            raise RegisterError("binding-entry.json workflow_id does not match package manifest")
        if workflow_manifest.get("workflow_id") != workflow_id:
            raise RegisterError("workflow/manifest.json workflow_id does not match package manifest")
        if not any(_is_workflow_member(name) for name in archive.namelist()):
            raise RegisterError("flow archive does not contain workflow/ files")
        return {
            "archive": archive,
            "workflow_id": workflow_id,
            "binding_entry": binding_entry,
        }
    except Exception:
        archive.close()
        raise


def _validate_workflow_id(value: object) -> str:
    if not isinstance(value, str):
        raise RegisterError("workflow_id must be a string")
    workflow_id = value.strip()
    if not workflow_id or not _SAFE_WORKFLOW_ID_PATTERN.fullmatch(workflow_id):
        raise RegisterError("workflow_id must contain only letters, numbers, dot, dash, or underscore")
    if workflow_id in {".", ".."}:
        raise RegisterError("workflow_id must not be a path traversal segment")
    return workflow_id


def _validate_archive_names(archive: zipfile.ZipFile) -> None:
    required_names = {
        "package-manifest.json",
        "binding-entry.json",
        "workflow/manifest.json",
    }
    names = set(archive.namelist())
    missing = sorted(required_names - names)
    if missing:
        raise RegisterError(f"flow archive missing required entries: {', '.join(missing)}")

    for name in names:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise RegisterError(f"unsafe archive entry path: {name}")


def _read_archive_json(archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
    try:
        payload = json.loads(archive.read(name).decode("utf-8"))
    except KeyError as exc:
        raise RegisterError(f"flow archive missing required entry: {name}") from exc
    except json.JSONDecodeError as exc:
        raise RegisterError(f"invalid JSON in flow archive entry {name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RegisterError(f"flow archive entry must be a JSON object: {name}")
    return payload


def _is_workflow_member(name: str) -> bool:
    return name.startswith("workflow/") and name != "workflow/" and not name.endswith("/")


def _extract_workflow(archive: zipfile.ZipFile, temp_workflow_dir: Path) -> int:
    installed_files = 0
    temp_workflow_dir.mkdir(parents=True, exist_ok=True)
    for info in archive.infolist():
        name = info.filename
        if not _is_workflow_member(name):
            continue
        relative_path = Path(name).relative_to("workflow")
        _validate_relative_workflow_path(relative_path)
        target_path = temp_workflow_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(archive.read(info))
        installed_files += 1
    if installed_files == 0:
        raise RegisterError("flow archive does not contain workflow files")
    return installed_files


def _validate_relative_workflow_path(path: Path) -> None:
    if path.is_absolute() or not path.parts:
        raise RegisterError("workflow archive entry must be a relative file path")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise RegisterError(f"unsafe workflow archive entry path: {path.as_posix()}")


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegisterError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RegisterError(f"{label} must be a JSON object")
    return payload


def _find_binding_index(binding_payload: dict[str, Any], workflow_id: str) -> int | None:
    workflows = binding_payload.get("workflows")
    if not isinstance(workflows, list):
        raise RegisterError("workflow binding config field 'workflows' must be a list")
    for index, item in enumerate(workflows):
        if not isinstance(item, dict):
            continue
        item_workflow_id = item.get("workflow_id")
        if isinstance(item_workflow_id, str) and item_workflow_id.strip() == workflow_id:
            return index
    return None


def _register_binding_entry(
    *,
    binding_path: Path,
    binding_payload: dict[str, Any],
    binding_entry: dict[str, Any],
    existing_index: int | None,
) -> None:
    workflows = binding_payload["workflows"]
    if existing_index is None:
        workflows.append(binding_entry)
    else:
        workflows[existing_index] = binding_entry
    _write_json_atomic(binding_path, binding_payload)


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
        payload = register_flow_package(
            runtime_skill_root=args.runtime_skill_root,
            flow_file=args.flow_file,
            force=args.force,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Register a .flow archive into durable-workflow-runtime"
    )
    parser.add_argument("--runtime-skill-root", default=str(DEFAULT_RUNTIME_SKILL_ROOT))
    parser.add_argument("--flow-file", required=True)
    parser.add_argument("--force", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
