from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PACK_SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_SKILL_ROOT = PACK_SKILL_ROOT.parent
_SAFE_WORKFLOW_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_EXCLUDED_FILE_NAMES = {".DS_Store"}
_EXCLUDED_DIR_NAMES = {"__pycache__"}
_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


class PackError(ValueError):
    pass


def build_flow_package(
    *,
    runtime_skill_root: str | Path,
    workflow_id: str,
    output_file: str | Path,
    force: bool = False,
) -> dict[str, Any]:
    runtime_root = _resolve_runtime_skill_root(runtime_skill_root)
    resolved_workflow_id = _validate_workflow_id(workflow_id)
    output_path = Path(output_file).expanduser().resolve()
    _validate_output_file(output_path, force=force)

    binding_path = runtime_root / "workflow-binding.json"
    workflows_root = runtime_root / "workflow-runtime" / "workflows"
    binding_payload = _load_json_object(binding_path, "workflow binding config")
    binding_entry = _resolve_binding_entry(binding_payload, resolved_workflow_id)
    workflow_dir = _resolve_workflow_dir(workflows_root, resolved_workflow_id)
    binding_entry = _attach_start_input_schema(
        runtime_skill_root=runtime_root,
        workflow_id=resolved_workflow_id,
        binding_entry=binding_entry,
    )

    package_manifest = _build_package_manifest(
        workflow_id=resolved_workflow_id,
        binding_entry=binding_entry,
    )
    included_files = _write_flow_archive(
        workflow_dir=workflow_dir,
        output_path=output_path,
        binding_entry=binding_entry,
        package_manifest=package_manifest,
    )

    return {
        "kind": "flow_package",
        "workflow_id": resolved_workflow_id,
        "output_file": str(output_path),
        "included_files": included_files,
        "size_bytes": output_path.stat().st_size,
        "package_manifest": "package-manifest.json",
    }


def _resolve_runtime_skill_root(runtime_skill_root: str | Path) -> Path:
    path = Path(runtime_skill_root).expanduser().resolve()
    required_paths = [
        path / "workflow-binding.json",
        path / "workflow-runtime",
        path / "workflow-runtime" / "runtime",
        path / "workflow-runtime" / "workflows",
    ]
    missing = [str(item) for item in required_paths if not item.exists()]
    if missing:
        raise PackError(f"missing durable-workflow-runtime paths: {', '.join(missing)}")
    return path


def _validate_workflow_id(workflow_id: str) -> str:
    if not isinstance(workflow_id, str):
        raise PackError("workflow_id must be a string")
    resolved = workflow_id.strip()
    if not resolved or not _SAFE_WORKFLOW_ID_PATTERN.fullmatch(resolved):
        raise PackError("workflow_id must contain only letters, numbers, dot, dash, or underscore")
    if resolved in {".", ".."}:
        raise PackError("workflow_id must not be a path traversal segment")
    return resolved


def _validate_output_file(output_path: Path, *, force: bool) -> None:
    if output_path.suffix != ".flow":
        raise PackError("output file must use the .flow extension")
    if output_path.exists() and not force:
        raise PackError(f"output file already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise PackError(f"missing {label}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PackError(f"{label} must be a JSON object")
    return payload


def _resolve_binding_entry(binding_payload: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    workflows = binding_payload.get("workflows")
    if not isinstance(workflows, list):
        raise PackError("workflow binding config field 'workflows' must be a list")

    for item in workflows:
        if not isinstance(item, dict):
            continue
        item_workflow_id = item.get("workflow_id")
        if isinstance(item_workflow_id, str) and item_workflow_id.strip() == workflow_id:
            return deepcopy(item)
    raise PackError(f"workflow is not published in binding catalog: {workflow_id}")


def _resolve_workflow_dir(workflows_root: Path, workflow_id: str) -> Path:
    workflow_dir = workflows_root / workflow_id
    if not workflow_dir.is_dir():
        raise PackError(f"configured workflow does not exist: {workflow_id}")
    manifest_path = workflow_dir / "manifest.json"
    manifest = _load_json_object(manifest_path, "workflow manifest")
    if manifest.get("workflow_id") != workflow_id:
        raise PackError(
            "workflow manifest workflow_id mismatch: "
            f"expected {workflow_id}, got {manifest.get('workflow_id')}"
        )
    return workflow_dir


def _attach_start_input_schema(
    *,
    runtime_skill_root: Path,
    workflow_id: str,
    binding_entry: dict[str, Any],
) -> dict[str, Any]:
    expected_schema = _load_workflow_start_input_schema(runtime_skill_root, workflow_id)
    current_schema = binding_entry.get("start_input_schema")
    if current_schema is None:
        binding_entry["start_input_schema"] = expected_schema
        return binding_entry
    if current_schema != expected_schema:
        raise PackError(
            "workflow binding start_input_schema does not match "
            f"WORKFLOW_INPUT_CONTRACT for {workflow_id}"
        )
    return binding_entry


def _load_workflow_start_input_schema(runtime_skill_root: Path, workflow_id: str) -> dict[str, Any]:
    runtime_root = runtime_skill_root / "workflow-runtime"
    runtime_root_text = str(runtime_root)
    if runtime_root_text not in sys.path:
        sys.path.insert(0, runtime_root_text)
    try:
        from runtime.module_loader import load_workflow_modules

        modules = load_workflow_modules(workflow_id)
    except Exception as exc:
        raise PackError(f"failed to load workflow modules for {workflow_id}: {exc}") from exc
    return modules["contract"].WORKFLOW_INPUT_CONTRACT.to_start_input_schema()


def _build_package_manifest(
    *,
    workflow_id: str,
    binding_entry: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "package_type": "durable-workflow-runtime.flow",
        "container": "zip",
        "workflow_id": workflow_id,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_skill": "durable-workflow-runtime:pack",
        "binding_entry": "binding-entry.json",
        "workflow_root": "workflow/",
        "workflow_manifest": "workflow/manifest.json",
        "start_input_schema": binding_entry["start_input_schema"],
    }


def _write_flow_archive(
    *,
    workflow_dir: Path,
    output_path: Path,
    binding_entry: dict[str, Any],
    package_manifest: dict[str, Any],
) -> int:
    included_files = 0
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(tmp_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            _write_json_entry(archive, "package-manifest.json", package_manifest)
            _write_json_entry(archive, "binding-entry.json", binding_entry)
            included_files += 2

            for path in _iter_packable_files(workflow_dir):
                archive.write(path, _archive_name(workflow_dir, path))
                included_files += 1
        tmp_path.replace(output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return included_files


def _write_json_entry(archive: zipfile.ZipFile, name: str, payload: dict[str, Any]) -> None:
    archive.writestr(name, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _iter_packable_files(workflow_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in workflow_dir.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(workflow_dir).parts
        if any(part in _EXCLUDED_DIR_NAMES for part in relative_parts):
            continue
        if path.name in _EXCLUDED_FILE_NAMES or path.suffix in _EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files)


def _archive_name(workflow_dir: Path, path: Path) -> str:
    return "workflow/" + path.relative_to(workflow_dir).as_posix()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = build_flow_package(
            runtime_skill_root=args.runtime_skill_root,
            workflow_id=args.workflow_id,
            output_file=args.output_file,
            force=args.force,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pack a durable-workflow-runtime workflow into a .flow archive"
    )
    parser.add_argument("--runtime-skill-root", default=str(DEFAULT_RUNTIME_SKILL_ROOT))
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--force", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
