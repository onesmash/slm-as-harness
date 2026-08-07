from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LAYOUT_VERSION = 1
HOST_IO_RELATIVE_ROOT = Path(".durable-workflow-runtime") / "host-io"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
MAX_HOST_ARTIFACT_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class HostIoLayout:
    run_id: str
    run_dir: Path
    responses_dir: Path
    observations_dir: Path
    artifacts_dir: Path
    start_request: Path
    latest_response: Path
    manifest: Path


def pending_start_request_path(repo_root: str | Path, workflow_id: str | None = None) -> Path:
    """Return a stable pre-start request path before a runtime run_id exists."""
    root = _host_io_root(repo_root)
    _ensure_directory(root, mode=0o700)
    pending_dir = root / "pending"
    _ensure_directory(pending_dir, mode=0o700)
    if workflow_id:
        return pending_dir / f"{_safe_id(workflow_id, field='workflow_id')}-start-request.json"
    return pending_dir / "start-request.json"


def ensure_run_layout(repo_root: str | Path, run_id: str) -> HostIoLayout:
    safe_run_id = _safe_id(run_id, field="run_id")
    root = _host_io_root(repo_root)
    _ensure_directory(root, mode=0o700)
    run_dir = root / safe_run_id
    _ensure_directory(run_dir, mode=0o700)
    layout = HostIoLayout(
        run_id=safe_run_id,
        run_dir=run_dir,
        responses_dir=run_dir / "responses",
        observations_dir=run_dir / "observations",
        artifacts_dir=run_dir / "artifacts",
        start_request=run_dir / "start-request.json",
        latest_response=run_dir / "latest-response.json",
        manifest=run_dir / "manifest.json",
    )
    for directory in (layout.responses_dir, layout.observations_dir, layout.artifacts_dir):
        _ensure_directory(directory, mode=0o700)
    return layout


def response_path(
    repo_root: str | Path,
    run_id: str,
    step_id: str,
    *,
    sequence: int | None = None,
) -> Path:
    return _step_path(
        ensure_run_layout(repo_root, run_id).responses_dir,
        step_id,
        sequence=sequence,
    )


def observation_path(
    repo_root: str | Path,
    run_id: str,
    step_id: str,
    *,
    sequence: int | None = None,
) -> Path:
    return _step_path(
        ensure_run_layout(repo_root, run_id).observations_dir,
        step_id,
        sequence=sequence,
    )


def artifact_path(repo_root: str | Path, run_id: str, relative_path: str | Path) -> Path:
    layout = ensure_run_layout(repo_root, run_id)
    safe_relative_path = _safe_relative_path(relative_path)
    _reject_symlink_components(layout.artifacts_dir, safe_relative_path.parent)
    path = layout.artifacts_dir / safe_relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(layout.artifacts_dir, safe_relative_path.parent)
    return path


def write_artifact(
    repo_root: str | Path,
    run_id: str,
    relative_path: str | Path,
    content: bytes | str,
    *,
    media_type: str = "application/octet-stream",
) -> dict[str, Any]:
    """Write one bounded host artifact and return a checksum-bearing reference."""

    if isinstance(content, str):
        content = content.encode("utf-8")
    if not isinstance(content, bytes):
        raise ValueError("artifact content must be bytes or text")
    if len(content) > MAX_HOST_ARTIFACT_BYTES:
        raise ValueError(f"artifact exceeds {MAX_HOST_ARTIFACT_BYTES} bytes")
    if not isinstance(media_type, str) or not media_type.strip() or len(media_type) > 128:
        raise ValueError("artifact media_type is invalid")
    if any(ord(char) < 0x20 for char in media_type):
        raise ValueError("artifact media_type contains control characters")
    path = artifact_path(repo_root, run_id, relative_path)
    if path.is_symlink():
        raise ValueError("refusing to replace symlink artifact")
    _write_bytes_atomic(path, content)
    root = _host_io_root(repo_root)
    relative = path.relative_to(root).as_posix()
    return {
        "uri": f"artifact://{run_id}/{relative}",
        "relative_path": relative,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "media_type": media_type.strip(),
    }


def read_artifact(repo_root: str | Path, run_id: str, relative_path: str | Path) -> bytes:
    safe_run_id = _safe_id(run_id, field="run_id")
    safe_relative_path = _safe_relative_path(relative_path)
    artifacts_dir = _host_io_root(repo_root) / safe_run_id / "artifacts"
    if not artifacts_dir.is_dir() or artifacts_dir.is_symlink():
        raise ValueError("artifact directory does not exist")
    _reject_symlink_components(artifacts_dir, safe_relative_path.parent)
    path = artifacts_dir / safe_relative_path
    if path.is_symlink() or not path.is_file():
        raise ValueError("artifact is not a regular file")
    if path.stat().st_size > MAX_HOST_ARTIFACT_BYTES:
        raise ValueError("artifact exceeds the host artifact limit")
    return path.read_bytes()


def host_io_root(repo_root: str | Path) -> Path:
    return _host_io_root(repo_root)


def is_host_io_path(repo_root: str | Path, path: str | Path) -> bool:
    candidate = Path(path).expanduser()
    if _path_contains_symlink(candidate):
        return False
    resolved_path = candidate.resolve(strict=False)
    try:
        resolved_path.relative_to(_host_io_root(repo_root))
    except ValueError:
        return False
    return True


def write_manifest(
    repo_root: str | Path,
    run_id: str,
    *,
    workflow_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    layout = ensure_run_layout(repo_root, run_id)
    payload: dict[str, Any] = {
        "layout_version": LAYOUT_VERSION,
        "run_id": layout.run_id,
        "workflow_id": workflow_id,
        "paths": {
            "run_dir": str(layout.run_dir),
            "start_request": str(layout.start_request),
            "latest_response": str(layout.latest_response),
            "responses_dir": str(layout.responses_dir),
            "observations_dir": str(layout.observations_dir),
            "artifacts_dir": str(layout.artifacts_dir),
        },
    }
    if extra:
        payload.update(extra)
    _write_json_atomic(layout.manifest, payload)
    return layout.manifest


def _host_io_root(repo_root: str | Path) -> Path:
    repo_path = Path(repo_root).expanduser().resolve()
    root = repo_path / HOST_IO_RELATIVE_ROOT
    if root.is_symlink():
        raise ValueError(f"host I/O root must not be a symlink: {root}")
    return root


def _step_path(directory: Path, step_id: str, *, sequence: int | None) -> Path:
    safe_step_id = _safe_id(step_id, field="step_id")
    prefix = f"{sequence:03d}_" if sequence is not None else ""
    path = directory / f"{prefix}{safe_step_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _safe_id(value: str, *, field: str) -> str:
    if not value or not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must contain only letters, numbers, dot, dash, or underscore")
    if value in {".", ".."}:
        raise ValueError(f"{field} must not be a path traversal segment")
    return value


def _safe_relative_path(path: str | Path) -> Path:
    relative = Path(path)
    if relative.is_absolute():
        raise ValueError("artifact path must be relative")
    if not relative.parts:
        raise ValueError("artifact path must not be empty")
    if relative.parts and len(relative.parts[0]) >= 2 and relative.parts[0][1] == ":":
        raise ValueError("artifact path must not contain a drive prefix")
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("artifact path must not contain empty or traversal segments")
    if any(any(ord(char) < 0x20 for char in part) for part in relative.parts):
        raise ValueError("artifact path must not contain control characters")
    return relative


def _ensure_directory(path: Path, *, mode: int) -> None:
    if path.is_symlink():
        raise ValueError(f"refusing to use symlink directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"host I/O path is not a real directory: {path}")
    os.chmod(path, mode)


def _reject_symlink_components(base: Path, relative: Path) -> None:
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"refusing to traverse symlink path component: {current}")


def _path_contains_symlink(path: Path) -> bool:
    if not path.is_absolute():
        path = (Path.cwd() / path).absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to replace symlink: {path}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to replace symlink: {path}")
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == serialized:
                return
        except (OSError, UnicodeError):
            pass
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        payload = _dispatch_cli(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Allocate durable-workflow host I/O paths")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pending_parser = subparsers.add_parser("pending-start")
    pending_parser.add_argument("--repo-root", required=True)
    pending_parser.add_argument("--workflow-id", required=False)

    ensure_parser = subparsers.add_parser("ensure-run")
    ensure_parser.add_argument("--repo-root", required=True)
    ensure_parser.add_argument("--run-id", required=True)
    ensure_parser.add_argument("--workflow-id", required=False)

    response_parser = subparsers.add_parser("response-path")
    response_parser.add_argument("--repo-root", required=True)
    response_parser.add_argument("--run-id", required=True)
    response_parser.add_argument("--step-id", required=True)
    response_parser.add_argument("--sequence", type=int, required=False)

    observation_parser = subparsers.add_parser("observation-path")
    observation_parser.add_argument("--repo-root", required=True)
    observation_parser.add_argument("--run-id", required=True)
    observation_parser.add_argument("--step-id", required=True)
    observation_parser.add_argument("--sequence", type=int, required=False)

    artifact_parser = subparsers.add_parser("artifact-path")
    artifact_parser.add_argument("--repo-root", required=True)
    artifact_parser.add_argument("--run-id", required=True)
    artifact_parser.add_argument("--relative-path", required=True)

    return parser


def _dispatch_cli(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "pending-start":
        path = pending_start_request_path(args.repo_root, args.workflow_id)
        return {
            "kind": "pending_start_request_path",
            "path": str(path),
        }

    if args.command == "ensure-run":
        layout = ensure_run_layout(args.repo_root, args.run_id)
        manifest = write_manifest(args.repo_root, args.run_id, workflow_id=args.workflow_id)
        return {
            "kind": "run_layout",
            "run_id": layout.run_id,
            "run_dir": str(layout.run_dir),
            "start_request": str(layout.start_request),
            "latest_response": str(layout.latest_response),
            "responses_dir": str(layout.responses_dir),
            "observations_dir": str(layout.observations_dir),
            "artifacts_dir": str(layout.artifacts_dir),
            "manifest": str(manifest),
        }

    if args.command == "response-path":
        path = response_path(args.repo_root, args.run_id, args.step_id, sequence=args.sequence)
        return {
            "kind": "response_path",
            "path": str(path),
        }

    if args.command == "observation-path":
        path = observation_path(args.repo_root, args.run_id, args.step_id, sequence=args.sequence)
        return {
            "kind": "observation_path",
            "path": str(path),
        }

    if args.command == "artifact-path":
        path = artifact_path(args.repo_root, args.run_id, args.relative_path)
        return {
            "kind": "artifact_path",
            "path": str(path),
        }

    raise ValueError(f"unknown host_io command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
