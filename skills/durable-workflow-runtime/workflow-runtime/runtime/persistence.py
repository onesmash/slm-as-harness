from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from runtime.errors import StateConflictError
from runtime.limits import validate_json_limits
from runtime.models import RunState


_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MAX_PERSISTED_STATE_BYTES = 8 * 1024 * 1024


class FileRunStateStore:
    """Small transactional file store for run state.

    Callers that perform a read/transition/write sequence must hold ``lock``.
    ``save`` also accepts an expected revision so accidental stale writes fail
    closed even when a caller forgets to coordinate its snapshot.
    """

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.runtime_root = self.repo_root / ".durable-workflow-runtime"
        if self.runtime_root.is_symlink():
            raise ValueError("runtime storage root must not be a symlink")
        self.runs_dir = self.runtime_root / "runs"
        if self.runs_dir.is_symlink():
            raise ValueError("run state directory must not be a symlink")

    def _validate_run_id(self, run_id: str) -> str:
        if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("run_id must contain only ASCII letters, digits, '_' or '-' (max 128 chars)")
        return run_id

    def _path_for(self, run_id: str) -> Path:
        run_id = self._validate_run_id(run_id)
        if self.runtime_root.is_symlink() or self.runs_dir.is_symlink():
            raise ValueError("run state root must not contain symlink directories")
        target = self.runs_dir / f"{run_id}.json"
        if target.is_symlink():
            raise ValueError("run state path must not be a symlink")
        try:
            target.parent.resolve(strict=False).relative_to(self.runs_dir.resolve(strict=False))
            target.resolve(strict=False).relative_to(self.runs_dir.resolve(strict=False))
        except ValueError as exc:
            raise ValueError("run state path escapes the runs directory") from exc
        return target

    def _lock_path_for(self, run_id: str) -> Path:
        target = self._path_for(run_id)
        lock_path = target.with_name(f".{target.name}.lock")
        if lock_path.is_symlink():
            raise ValueError("run lock path must not be a symlink")
        try:
            lock_path.resolve(strict=False).relative_to(self.runs_dir)
        except ValueError as exc:
            raise ValueError("run lock path escapes the runs directory") from exc
        return lock_path

    @contextmanager
    def lock(self, run_id: str) -> Iterator[dict[str, object]]:
        self.runs_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = self._lock_path_for(run_id)
        open_flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            open_flags |= os.O_NOFOLLOW
        descriptor = os.open(lock_path, open_flags, 0o600)
        try:
            wait_started = time.monotonic()
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            waited_ms = round((time.monotonic() - wait_started) * 1000, 3)
            yield {
                "waited_ms": waited_ms,
                "contended": waited_ms >= 1.0,
            }
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def save(
        self,
        run_state: RunState,
        *,
        expected_revision: int | None = None,
        _lock_held: bool = False,
    ) -> Path:
        if not _lock_held:
            with self.lock(run_state.run_id):
                return self.save(
                    run_state,
                    expected_revision=expected_revision,
                    _lock_held=True,
                )
        return self._save_unlocked(run_state, expected_revision=expected_revision)

    def _save_unlocked(
        self,
        run_state: RunState,
        *,
        expected_revision: int | None = None,
    ) -> Path:
        self.runs_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self._path_for(run_state.run_id)
        if expected_revision is not None:
            current = self._load_path(target)
            current_revision = current.revision if current is not None else 0
            if current_revision != expected_revision:
                raise StateConflictError(
                    f"run state revision conflict for {run_state.run_id}: "
                    f"expected {expected_revision}, found {current_revision}"
                )

        payload = json.dumps(
            run_state.to_dict(),
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        payload_bytes = payload.encode("utf-8")
        if len(payload_bytes) > MAX_PERSISTED_STATE_BYTES:
            raise ValueError(
                f"run state exceeds persisted size limit of {MAX_PERSISTED_STATE_BYTES} bytes"
            )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=self.runs_dir,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, target)
            self._fsync_directory()
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        return target

    def load(self, run_id: str) -> RunState | None:
        return self._load_path(self._path_for(run_id))

    def _load_path(self, target: Path) -> RunState | None:
        if not target.exists():
            return None
        if target.is_symlink() or not target.is_file():
            raise ValueError("run state path must be a regular file")
        if target.stat().st_size > MAX_PERSISTED_STATE_BYTES:
            raise ValueError(
                f"run state exceeds persisted size limit of {MAX_PERSISTED_STATE_BYTES} bytes"
            )
        payload = json.loads(target.read_text(encoding="utf-8"))
        validate_json_limits(
            payload,
            path="run_state",
            max_bytes=MAX_PERSISTED_STATE_BYTES,
        )
        return RunState.from_dict(payload)

    def _fsync_directory(self) -> None:
        descriptor = os.open(self.runs_dir, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
