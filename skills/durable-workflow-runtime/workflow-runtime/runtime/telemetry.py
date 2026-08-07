from __future__ import annotations

import fcntl
import json
import math
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_.:/-]{1,256}$")
MAX_TELEMETRY_EVENTS = 4096
MAX_TELEMETRY_BYTES = 2 * 1024 * 1024
MAX_METRIC_KEYS = 32
MAX_METRIC_LABEL_LENGTH = 256


def _iso_utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RuntimeTelemetry:
    """Bounded, best-effort operational metrics outside RunState.

    Telemetry is intentionally numeric and label-only. It never accepts a raw
    payload, exception repr, prompt, or verifier output, and a telemetry write
    failure must not change workflow protocol semantics.
    """

    def __init__(
        self,
        repo_root: str | Path,
        *,
        max_events: int = MAX_TELEMETRY_EVENTS,
        max_bytes: int = MAX_TELEMETRY_BYTES,
    ) -> None:
        if max_events < 1 or max_bytes < 1024:
            raise ValueError("telemetry limits are invalid")
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.runtime_root = self.repo_root / ".durable-workflow-runtime"
        if self.runtime_root.is_symlink():
            raise ValueError("runtime storage root must not be a symlink")
        self.root = self.runtime_root / "telemetry"
        self.events_path = self.root / "events.jsonl"
        self.lock_path = self.root / ".events.lock"
        self.max_events = max_events
        self.max_bytes = max_bytes

    def record(
        self,
        event: str,
        *,
        run_id: str | None = None,
        workflow_id: str | None = None,
        step_id: str | None = None,
        labels: dict[str, str] | None = None,
        metrics: dict[str, int | float | bool] | None = None,
    ) -> bool:
        try:
            payload = self._build_event(
                event,
                run_id=run_id,
                workflow_id=workflow_id,
                step_id=step_id,
                labels=labels,
                metrics=metrics,
            )
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            self._ensure_private_directory(self.root)
            descriptor = self._open_lock()
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                self._append_and_trim(payload)
            finally:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)
            return True
        except (OSError, TypeError, ValueError):
            return False

    def read_events(self) -> list[dict[str, Any]]:
        if (
            self.runtime_root.is_symlink()
            or self.root.is_symlink()
            or not self.events_path.is_file()
            or self.events_path.is_symlink()
        ):
            return []
        if self.events_path.stat().st_size > self.max_bytes:
            return []
        result: list[dict[str, Any]] = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                result.append(value)
        return result[-self.max_events :]

    def _build_event(
        self,
        event: str,
        *,
        run_id: str | None,
        workflow_id: str | None,
        step_id: str | None,
        labels: dict[str, str] | None,
        metrics: dict[str, int | float | bool] | None,
    ) -> dict[str, Any]:
        event = self._validate_label(event, "event")
        payload: dict[str, Any] = {"timestamp": _iso_utc_now(), "event": event}
        for field_name, value in (
            ("run_id", run_id),
            ("workflow_id", workflow_id),
            ("step_id", step_id),
        ):
            if value is not None:
                payload[field_name] = self._validate_label(value, field_name)
        if labels is not None:
            if not isinstance(labels, dict) or len(labels) > MAX_METRIC_KEYS:
                raise ValueError("telemetry labels are invalid")
            payload["labels"] = {
                self._validate_label(key, "label key"): self._validate_label(value, "label")
                for key, value in labels.items()
            }
        if metrics is not None:
            if not isinstance(metrics, dict) or len(metrics) > MAX_METRIC_KEYS:
                raise ValueError("telemetry metrics are invalid")
            normalized: dict[str, int | float | bool] = {}
            for key, value in metrics.items():
                key = self._validate_label(key, "metric key")
                if (
                    not isinstance(value, (int, float, bool))
                    or isinstance(value, float) and not math.isfinite(value)
                ):
                    raise ValueError("telemetry metric values must be finite numbers or booleans")
                normalized[key] = value
            payload["metrics"] = normalized
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        if len(encoded.encode("utf-8")) > 16 * 1024:
            raise ValueError("telemetry event is too large")
        return payload

    def _append_and_trim(self, payload: dict[str, Any]) -> None:
        encoded_line = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode("utf-8")
        self.events_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.events_path.is_symlink():
            raise OSError("telemetry file must not be a symlink")
        with open(self.events_path, "ab") as telemetry_file:
            if self.events_path.stat().st_mode & 0o077:
                os.fchmod(telemetry_file.fileno(), 0o600)
            telemetry_file.write(encoded_line)
            telemetry_file.flush()
            os.fsync(telemetry_file.fileno())
        if self.events_path.stat().st_size <= self.max_bytes:
            return
        lines = self.events_path.read_bytes().splitlines()
        retained: list[bytes] = []
        total = 0
        for line in reversed(lines[-self.max_events :]):
            line_with_newline = line + b"\n"
            if total + len(line_with_newline) > self.max_bytes:
                break
            retained.append(line_with_newline)
            total += len(line_with_newline)
        retained.reverse()
        self._rewrite_bytes(b"".join(retained))

    def _rewrite_bytes(self, content: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.events_path.name}.",
            suffix=".tmp",
            dir=self.events_path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.events_path)
            directory_descriptor = os.open(self.events_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def _open_lock(self) -> int:
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.lock_path, flags, 0o600)
        os.fchmod(descriptor, 0o600)
        return descriptor

    @staticmethod
    def _ensure_private_directory(path: Path) -> None:
        if path.is_symlink() or not path.is_dir():
            raise OSError("telemetry directory must be a real directory")
        os.chmod(path, 0o700)

    @staticmethod
    def _validate_label(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not _SAFE_LABEL.fullmatch(value):
            raise ValueError(f"telemetry {field_name} is invalid")
        if len(value) > MAX_METRIC_LABEL_LENGTH:
            raise ValueError(f"telemetry {field_name} is too long")
        return value
