from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from runtime.errors import ArtifactStoreError


_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_ARTIFACT_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_ROOT_NAME = ".durable-workflow-runtime"
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_ARTIFACTS_PER_RUN = 256
MAX_ARTIFACT_BYTES_PER_RUN = 64 * 1024 * 1024
MAX_MEDIA_TYPE_LENGTH = 128


def _iso_utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ArtifactReference:
    """A routing-only reference; business code owns the artifact contents."""

    artifact_id: str
    relative_path: str
    size_bytes: int
    sha256: str
    media_type: str
    created_at: str
    kind: str = "diagnostic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "created_at": self.created_at,
            "kind": self.kind,
        }


class ArtifactStore:
    """Small content-addressed store for bounded runtime diagnostics.

    The store intentionally exposes references only. Runtime state can retain a
    checksum, size and path reference without embedding transcripts or raw
    output. Files are private to the current user and written atomically.
    """

    def __init__(
        self,
        repo_root: str | Path,
        *,
        max_artifact_bytes: int = MAX_ARTIFACT_BYTES,
        max_artifacts_per_run: int = MAX_ARTIFACTS_PER_RUN,
        max_bytes_per_run: int = MAX_ARTIFACT_BYTES_PER_RUN,
    ) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.runtime_root = self.repo_root / _ARTIFACT_ROOT_NAME
        if self.runtime_root.is_symlink():
            raise ValueError("runtime storage root must not be a symlink")
        self.root = self.runtime_root / "artifacts"
        self.max_artifact_bytes = max_artifact_bytes
        self.max_artifacts_per_run = max_artifacts_per_run
        self.max_bytes_per_run = max_bytes_per_run
        if (
            max_artifact_bytes < 1
            or max_artifacts_per_run < 1
            or max_bytes_per_run < max_artifact_bytes
        ):
            raise ValueError("artifact store limits are invalid")

    def put_bytes(
        self,
        run_id: str,
        content: bytes,
        *,
        media_type: str = "application/octet-stream",
        kind: str = "diagnostic",
    ) -> ArtifactReference:
        run_id = self._validate_run_id(run_id)
        if not isinstance(content, bytes):
            raise ArtifactStoreError("artifact content must be bytes")
        if len(content) > self.max_artifact_bytes:
            raise ArtifactStoreError(
                f"artifact exceeds {self.max_artifact_bytes} bytes",
            )
        media_type = self._validate_label(media_type, "media_type")
        kind = self._validate_label(kind, "kind")

        run_dir = self._run_dir(run_id, create=True)
        with self._run_lock(run_dir):
            digest = hashlib.sha256(content).hexdigest()
            target = run_dir / f"{digest}.bin"
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ArtifactStoreError("artifact target must be a regular file")
            if target.is_file():
                self._verify_file(target, expected_digest=digest, expected_size=len(content))
            else:
                self._enforce_run_budget(run_dir, len(content))
                self._write_file_atomically(target, content)

        return ArtifactReference(
            artifact_id=digest,
            relative_path=target.relative_to(self.repo_root).as_posix(),
            size_bytes=len(content),
            sha256=digest,
            media_type=media_type,
            created_at=_iso_utc_now(),
            kind=kind,
        )

    def put_json(
        self,
        run_id: str,
        value: Any,
        *,
        media_type: str = "application/json",
        kind: str = "diagnostic",
    ) -> ArtifactReference:
        try:
            content = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ArtifactStoreError("artifact value must be finite JSON") from exc
        return self.put_bytes(
            run_id,
            content,
            media_type=media_type,
            kind=kind,
        )

    def read_bytes(self, reference: ArtifactReference | dict[str, Any]) -> bytes:
        normalized = self._normalize_reference(reference)
        run_id = self._run_id_from_reference(normalized)
        target = self._run_dir(run_id, create=False) / f"{normalized['artifact_id']}.bin"
        if target.is_symlink() or not target.is_file():
            raise ArtifactStoreError("artifact reference does not resolve to a regular file")
        content = target.read_bytes()
        if len(content) != normalized["size_bytes"]:
            raise ArtifactStoreError("artifact size does not match its reference")
        if hashlib.sha256(content).hexdigest() != normalized["sha256"]:
            raise ArtifactStoreError("artifact checksum does not match its reference")
        return content

    def list_references(self, run_id: str, *, kind: str = "diagnostic") -> list[ArtifactReference]:
        run_id = self._validate_run_id(run_id)
        if not self.root.exists():
            return []
        run_dir = self._run_dir(run_id, create=False)
        if not run_dir.exists():
            return []
        references: list[ArtifactReference] = []
        for path in sorted(run_dir.glob("*.bin")):
            if path.is_symlink() or not path.is_file():
                raise ArtifactStoreError("artifact directory contains a non-regular file")
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if path.stem != digest:
                raise ArtifactStoreError("artifact filename does not match its checksum")
            references.append(
                ArtifactReference(
                    artifact_id=digest,
                    relative_path=path.relative_to(self.repo_root).as_posix(),
                    size_bytes=len(content),
                    sha256=digest,
                    media_type="application/octet-stream",
                    created_at=_iso_utc_now(),
                    kind=kind,
                )
            )
        return references

    def remove_run(self, run_id: str) -> bool:
        """Remove only one validated run directory for explicit retention cleanup."""

        run_id = self._validate_run_id(run_id)
        if not self.root.exists():
            return False
        run_dir = self._run_dir(run_id, create=False)
        if not run_dir.exists():
            return False
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise ArtifactStoreError("artifact run directory must be a real directory")
        for path in run_dir.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ArtifactStoreError("refusing to remove unexpected artifact entry")
            path.unlink()
        run_dir.rmdir()
        self._fsync_directory(self.root)
        return True

    def _run_dir(self, run_id: str, *, create: bool) -> Path:
        run_id = self._validate_run_id(run_id)
        if self.runtime_root.is_symlink() or self.root.is_symlink():
            raise ArtifactStoreError("artifact roots must not be symlink directories")
        if create:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        elif not self.root.exists():
            return self.root / run_id
        if self.root.is_symlink() or not self.root.is_dir():
            raise ArtifactStoreError("artifact root must be a real directory")
        run_dir = self.root / run_id
        if run_dir.is_symlink():
            raise ArtifactStoreError("artifact run directory must not be a symlink")
        if create:
            run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if run_dir.exists() and not run_dir.is_dir():
            raise ArtifactStoreError("artifact run directory must be a directory")
        try:
            run_dir.resolve(strict=False).relative_to(self.root.resolve(strict=False))
        except ValueError as exc:
            raise ArtifactStoreError("artifact path escapes the artifact root") from exc
        return run_dir

    def _enforce_run_budget(self, run_dir: Path, content_size: int) -> None:
        existing = 0
        count = 0
        for path in run_dir.glob("*.bin"):
            if path.is_symlink() or not path.is_file():
                raise ArtifactStoreError("artifact directory contains an unsafe entry")
            count += 1
            existing += path.stat().st_size
        if count >= self.max_artifacts_per_run:
            raise ArtifactStoreError("artifact count limit exceeded")
        if existing + content_size > self.max_bytes_per_run:
            raise ArtifactStoreError("artifact byte budget exceeded")

    def _write_file_atomically(self, target: Path, content: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, target)
            self._fsync_directory(target.parent)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    @contextmanager
    def _run_lock(self, run_dir: Path):
        lock_path = run_dir / ".artifacts.lock"
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise ArtifactStoreError("cannot create artifact lock") from exc
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @staticmethod
    def _verify_file(path: Path, *, expected_digest: str, expected_size: int) -> None:
        content = path.read_bytes()
        if len(content) != expected_size or hashlib.sha256(content).hexdigest() != expected_digest:
            raise ArtifactStoreError("existing artifact does not match its content address")

    @staticmethod
    def _validate_run_id(run_id: str) -> str:
        if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
            raise ArtifactStoreError("run_id is not safe for artifact storage")
        return run_id

    @staticmethod
    def _validate_label(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > MAX_MEDIA_TYPE_LENGTH:
            raise ArtifactStoreError(f"{field_name} is invalid")
        if any(ord(char) < 0x20 for char in value):
            raise ArtifactStoreError(f"{field_name} contains control characters")
        return value.strip()

    @staticmethod
    def _normalize_reference(reference: ArtifactReference | dict[str, Any]) -> dict[str, Any]:
        payload = reference.to_dict() if isinstance(reference, ArtifactReference) else reference
        if not isinstance(payload, dict):
            raise ArtifactStoreError("artifact reference must be an object")
        artifact_id = payload.get("artifact_id")
        size_bytes = payload.get("size_bytes")
        sha256 = payload.get("sha256")
        relative_path = payload.get("relative_path")
        if (
            not isinstance(artifact_id, str)
            or not _ARTIFACT_ID_PATTERN.fullmatch(artifact_id)
            or not isinstance(sha256, str)
            or sha256 != artifact_id
            or not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes < 0
            or size_bytes > MAX_ARTIFACT_BYTES
            or not isinstance(relative_path, str)
        ):
            raise ArtifactStoreError("artifact reference is invalid")
        return {
            "artifact_id": artifact_id,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "relative_path": relative_path,
        }

    def _run_id_from_reference(self, reference: dict[str, Any]) -> str:
        relative = Path(reference["relative_path"])
        if relative.is_absolute() or relative.parts[:2] != (".durable-workflow-runtime", "artifacts"):
            raise ArtifactStoreError("artifact reference path is outside the artifact root")
        if len(relative.parts) != 4 or relative.parts[3] != f"{reference['artifact_id']}.bin":
            raise ArtifactStoreError("artifact reference path does not match its checksum")
        run_id = relative.parts[2]
        self._validate_run_id(run_id)
        return run_id

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
