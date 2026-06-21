from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LAYOUT_VERSION = 1
HOST_IO_RELATIVE_ROOT = Path(".durable-workflow-runtime") / "host-io"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


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
    pending_dir = _host_io_root(repo_root) / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    if workflow_id:
        return pending_dir / f"{_safe_id(workflow_id, field='workflow_id')}-start-request.json"
    return pending_dir / "start-request.json"


def ensure_run_layout(repo_root: str | Path, run_id: str) -> HostIoLayout:
    safe_run_id = _safe_id(run_id, field="run_id")
    run_dir = _host_io_root(repo_root) / safe_run_id
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
    for directory in (
        layout.run_dir,
        layout.responses_dir,
        layout.observations_dir,
        layout.artifacts_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
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
    path = layout.artifacts_dir / safe_relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def host_io_root(repo_root: str | Path) -> Path:
    return _host_io_root(repo_root)


def is_host_io_path(repo_root: str | Path, path: str | Path) -> bool:
    resolved_path = Path(path).expanduser().resolve()
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
    return Path(repo_root).expanduser().resolve() / HOST_IO_RELATIVE_ROOT


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
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("artifact path must not contain empty or traversal segments")
    return relative


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


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
