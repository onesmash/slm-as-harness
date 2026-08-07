from __future__ import annotations

import importlib
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

from runtime.errors import VerifierExecutionError, WorkflowExecutionError
from runtime.limits import (
    DEFAULT_RUNTIME_LIMITS,
    PayloadLimitError,
    validate_json_limits,
)


_SAFE_VERIFIER_EXECUTABLES = {
    "false",
    "python",
    "python3",
    "test",
    "true",
}
_FORBIDDEN_ARG_TOKENS = {";", "&&", "||", "|", "&", ">", ">>", "<", "<<"}
_TRUSTED_EXECUTABLE_DIRS = tuple(
    Path(path)
    for path in (
        Path(sys.executable).resolve().parent,
        "/bin",
        "/usr/bin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
    )
)


def run_step_verifier(*, repo_root: str | Path, modules: dict, verifier, run_state, observation):
    if verifier is None:
        return None
    if observation.status not in verifier.run_on_status:
        return None
    repo_path = Path(repo_root).expanduser().resolve()
    if not repo_path.is_dir():
        raise VerifierExecutionError("verifier working directory is not a directory")
    if verifier.kind == "shell_command":
        return _run_argv_verifier(verifier, repo_path)
    if verifier.kind != "python_callable":
        raise WorkflowExecutionError(f"unsupported verifier kind: {verifier.kind}")
    try:
        module_name, function_name = verifier.ref.split(":", 1)
    except ValueError as exc:
        raise VerifierExecutionError("python verifier reference must be module:function") from exc
    try:
        module = importlib.import_module(module_name)
        verifier_fn = getattr(module, function_name)
    except Exception as exc:
        raise WorkflowExecutionError(f"failed to load verifier {verifier.ref}: {exc}") from exc
    try:
        result = verifier_fn(
            repo_root=str(repo_path),
            run_id=run_state.run_id,
            step_id=observation.step_id,
            observation=observation.to_dict(),
            state=run_state.graph_state if isinstance(run_state.graph_state, dict) else None,
        )
        return _normalize_verifier_result(result)
    except Exception as exc:
        if isinstance(exc, VerifierExecutionError):
            raise
        raise WorkflowExecutionError(f"verifier execution failed: {exc}") from exc


def _normalize_verifier_result(result: object) -> dict:
    """Validate the callable verifier boundary before the engine consumes it."""

    if not isinstance(result, dict):
        raise VerifierExecutionError("python verifier must return an object")
    passed = result.get("passed")
    if not isinstance(passed, bool):
        raise VerifierExecutionError("python verifier result.passed must be a boolean")
    message = result.get("message")
    if not isinstance(message, str) or not message.strip():
        raise VerifierExecutionError("python verifier result.message must be non-empty text")
    details = result.get("details", {})
    if not isinstance(details, dict):
        raise VerifierExecutionError("python verifier result.details must be an object")
    normalized = {
        "passed": passed,
        "message": message.strip(),
        "details": details,
    }
    try:
        validate_json_limits(
            normalized,
            path="verifier_result",
            limits=DEFAULT_RUNTIME_LIMITS,
            max_bytes=DEFAULT_RUNTIME_LIMITS.max_verifier_output_bytes,
        )
    except (PayloadLimitError, ValueError) as exc:
        raise VerifierExecutionError(f"python verifier result is invalid: {exc}") from exc
    return normalized


def _run_argv_verifier(verifier, repo_path: Path) -> dict:
    argv = _parse_allowlisted_argv(verifier.ref)
    timeout_seconds = verifier.timeout_seconds
    if (
        not isinstance(timeout_seconds, (int, float))
        or isinstance(timeout_seconds, bool)
        or timeout_seconds <= 0
        or timeout_seconds > 300
    ):
        raise VerifierExecutionError("verifier timeout must be between 0 and 300 seconds")

    try:
        process = subprocess.Popen(
            argv,
            cwd=repo_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            close_fds=True,
            env={
                "PATH": os.pathsep.join(str(path) for path in _TRUSTED_EXECUTABLE_DIRS),
                "LANG": "C.UTF-8",
            },
        )
    except OSError as exc:
        raise VerifierExecutionError(
            f"failed to start allowlisted verifier executable {Path(argv[0]).name}"
        ) from exc
    stdout_buffer = _LimitedBuffer(DEFAULT_RUNTIME_LIMITS.max_verifier_output_bytes)
    stderr_buffer = _LimitedBuffer(DEFAULT_RUNTIME_LIMITS.max_verifier_output_bytes)
    readers = [
        threading.Thread(target=_drain_pipe, args=(process.stdout, stdout_buffer), daemon=True),
        threading.Thread(target=_drain_pipe, args=(process.stderr, stderr_buffer), daemon=True),
    ]
    for reader in readers:
        reader.start()

    timed_out = False
    try:
        returncode = process.wait(timeout=float(timeout_seconds))
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_group(process)
        try:
            returncode = process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            returncode = process.wait(timeout=2)
    finally:
        for reader in readers:
            reader.join(timeout=2)
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()

    stdout = stdout_buffer.text()
    stderr = stderr_buffer.text()
    details = {
        "executable": Path(argv[0]).name,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "output_truncated": stdout_buffer.truncated or stderr_buffer.truncated,
    }
    if timed_out:
        return {
            "passed": False,
            "message": "shell verifier timed out",
            "details": {**details, "timed_out": True},
        }
    return {
        "passed": returncode == 0,
        "message": (
            "shell verifier passed"
            if returncode == 0
            else "shell verifier failed"
        ),
        "details": details,
    }


def _parse_allowlisted_argv(command: str) -> list[str]:
    if not isinstance(command, str) or not command.strip():
        raise VerifierExecutionError("shell verifier command must be non-empty")
    if "\x00" in command or "\n" in command or "\r" in command:
        raise VerifierExecutionError("shell verifier command contains forbidden control characters")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        raise VerifierExecutionError("shell verifier command has invalid quoting") from exc
    if not argv:
        raise VerifierExecutionError("shell verifier command must contain an executable")
    if any(token in _FORBIDDEN_ARG_TOKENS for token in argv[1:]):
        raise VerifierExecutionError("shell verifier command contains forbidden shell syntax")
    if "/" in argv[0] or "\\" in argv[0]:
        raise VerifierExecutionError("shell verifier executable must be selected by name")
    executable_name = Path(argv[0]).name
    if executable_name not in _SAFE_VERIFIER_EXECUTABLES:
        raise VerifierExecutionError(
            f"shell verifier executable is not allowlisted: {executable_name}"
        )
    executable = _resolve_allowlisted_executable(argv[0])
    if executable is None:
        raise VerifierExecutionError(f"shell verifier executable is unavailable: {executable_name}")
    argv[0] = str(executable)
    return argv


def _resolve_allowlisted_executable(executable_name: str) -> Path | None:
    candidate = shutil.which(executable_name)
    if candidate is None:
        return None
    try:
        resolved = Path(candidate).resolve(strict=True)
    except OSError:
        return None
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        return None
    for trusted_dir in _TRUSTED_EXECUTABLE_DIRS:
        try:
            resolved.relative_to(trusted_dir)
            return resolved
        except ValueError:
            continue
    return None


class _LimitedBuffer:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._chunks: list[bytes] = []
        self._size = 0
        self.truncated = False

    def append(self, chunk: bytes) -> None:
        remaining = self.limit - self._size
        if remaining > 0:
            self._chunks.append(chunk[:remaining])
            self._size += min(len(chunk), remaining)
        if len(chunk) > remaining:
            self.truncated = True

    def text(self) -> str:
        return b"".join(self._chunks).decode("utf-8", errors="replace").strip()


def _drain_pipe(stream, buffer: _LimitedBuffer) -> None:
    if stream is None:
        return
    while True:
        chunk = stream.read(8192)
        if not chunk:
            return
        buffer.append(chunk)


def _terminate_process_group(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
