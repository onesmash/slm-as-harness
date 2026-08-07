from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from runtime.artifacts import ArtifactStore
from runtime.persistence import FileRunStateStore


@dataclass(frozen=True)
class RetentionPolicy:
    """Explicit cleanup policy; no cleanup is run implicitly by resume."""

    terminal_run_ttl_seconds: int = 7 * 24 * 60 * 60

    def __post_init__(self) -> None:
        if self.terminal_run_ttl_seconds < 0:
            raise ValueError("terminal_run_ttl_seconds must be non-negative")


def cleanup_expired_terminal_runs(
    repo_root: str | Path,
    *,
    policy: RetentionPolicy = RetentionPolicy(),
    now: datetime | None = None,
) -> dict[str, Any]:
    """Remove only expired terminal runs and their own artifact directory.

    This is an explicit operational action. It never follows symlinks, never
    scans outside the runtime-owned ``runs`` and ``artifacts`` roots, and skips
    malformed or non-terminal state instead of guessing ownership.
    """

    root = Path(repo_root).expanduser().resolve() / ".durable-workflow-runtime"
    if root.is_symlink():
        return {"removed_runs": [], "skipped": 1}
    runs_dir = root / "runs"
    cutoff = (now or datetime.now(UTC)) - timedelta(seconds=policy.terminal_run_ttl_seconds)
    removed_runs: list[str] = []
    removed_host_io: list[str] = []
    skipped = 0
    if not runs_dir.is_dir() or runs_dir.is_symlink():
        return {
            "removed_runs": removed_runs,
            "removed_host_io": removed_host_io,
            "skipped": skipped,
        }

    artifact_store = ArtifactStore(root.parent)
    state_store = FileRunStateStore(root.parent)
    host_io_root = root / "host-io"
    host_io_root_is_safe = not host_io_root.is_symlink()
    if host_io_root.exists() and not host_io_root.is_dir():
        host_io_root_is_safe = False
    if not host_io_root_is_safe:
        skipped += 1
    for state_path in sorted(runs_dir.glob("*.json")):
        if state_path.is_symlink() or not state_path.is_file():
            skipped += 1
            continue
        run_id = state_path.stem
        try:
            state_store._validate_run_id(run_id)
            with state_store.lock(run_id):
                state_path = state_store._path_for(run_id)
                if state_path.is_symlink() or not state_path.is_file():
                    skipped += 1
                    continue
                state = state_store.load(run_id)
                if state is None:
                    skipped += 1
                    continue
                updated_at = _parse_timestamp(state.updated_at)
                if state.status not in {"done", "failed_terminal"} or updated_at > cutoff:
                    continue
                if state_path.name != f"{state.run_id}.json":
                    skipped += 1
                    continue
                state_path.unlink()
                try:
                    artifact_store.remove_run(run_id)
                except Exception:
                    # State is already removed, but do not broaden deletion to an
                    # unexpected artifact entry. Surface the cleanup degradation.
                    skipped += 1
                if host_io_root_is_safe:
                    host_io_path = host_io_root / run_id
                    try:
                        if _remove_owned_tree(host_io_path):
                            removed_host_io.append(run_id)
                    except (OSError, ValueError):
                        skipped += 1
                removed_runs.append(run_id)
        except (OSError, TypeError, ValueError, KeyError):
            skipped += 1

    if removed_runs:
        _fsync_directory(runs_dir)
    return {
        "removed_runs": removed_runs,
        "removed_host_io": removed_host_io,
        "skipped": skipped,
    }


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _remove_owned_tree(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_symlink():
        raise ValueError("retention refuses to follow a host I/O symlink")
    if not path.is_dir():
        raise ValueError("host I/O run path must be a directory")
    for child in path.iterdir():
        if child.is_symlink():
            raise ValueError("retention refuses to remove a symlink entry")
        if child.is_dir():
            _remove_owned_tree(child)
        elif child.is_file():
            child.unlink()
        else:
            raise ValueError("retention found an unsupported host I/O entry")
    path.rmdir()
    return True
