from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import host_io


ERROR_EXIT_CODES = {
    "usage_error": 2,
    "input_error": 3,
    "bootstrap_error": 4,
    "protocol_error": 5,
    "observation_validation_error": 6,
    "execution_error": 7,
    "response_write_error": 8,
}
SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_HOST_PATH = SKILL_ROOT / "workflow-runtime" / "adapters" / "skill_host.py"
MAX_REQUEST_FILE_BYTES = 512 * 1024
MAX_OBSERVATION_FILE_BYTES = 1024 * 1024


class UnsafeHostIoPathError(ValueError):
    pass


class UnsafeResponseFilePathError(UnsafeHostIoPathError):
    pass


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    response_file = Path(args.response_file).resolve()

    try:
        repo_root = _resolve_repo_root(args.repo_root)
        _validate_command_host_io_paths(repo_root, args, response_file)
        skill_host = _load_skill_host()
        if args.command == "start":
            request = _load_json_object(
                Path(args.request_file),
                required_fields={"task_input", "context", "constraints"},
                max_bytes=MAX_REQUEST_FILE_BYTES,
            )
            response = skill_host.start(str(repo_root), request, workflow_id=args.workflow_id)
            _validate_start_response(response)
            _write_json_atomic(response_file, response)
            _print_success_status(response, response_file)
            return 0
        if args.command == "preflight":
            response = skill_host.preflight(str(repo_root), args.workflow_id)
            _validate_preflight_response(response)
            _write_json_atomic(response_file, response)
            _print_success_status(response, response_file)
            return 0
        else:
            observation = _load_json_object(
                Path(args.observation_file),
                required_fields={"run_id", "step_id", "status", "summary", "structured_output"},
                max_bytes=MAX_OBSERVATION_FILE_BYTES,
            )
            if observation.get("run_id") != args.run_id:
                raise skill_host.ObservationValidationError(
                    "observation run_id does not match CLI run_id"
                )
            response = skill_host.resume(str(repo_root), args.run_id, observation)
            _validate_resume_response(response)
            _write_json_atomic(response_file, response)
            _print_success_status(response, response_file)
        return 0
    except SystemExit:
        raise
    except Exception as exc:
        return _handle_error(exc, response_file)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prompt workflow bridge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--repo-root", required=True)
    start_parser.add_argument("--request-file", required=True)
    start_parser.add_argument("--response-file", required=True)
    start_parser.add_argument("--workflow-id", required=False)
    start_parser.add_argument("--allow-unsafe-host-io-paths", action="store_true")

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("preflight_command", choices=["install-deps"])
    preflight_parser.add_argument("--repo-root", required=True)
    preflight_parser.add_argument("--workflow-id", required=True)
    preflight_parser.add_argument("--response-file", required=True)
    preflight_parser.add_argument("--allow-unsafe-host-io-paths", action="store_true")

    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument("--repo-root", required=True)
    resume_parser.add_argument("--run-id", required=True)
    resume_parser.add_argument("--observation-file", required=True)
    resume_parser.add_argument("--response-file", required=True)
    resume_parser.add_argument("--allow-unsafe-host-io-paths", action="store_true")
    return parser


def _resolve_repo_root(repo_root: str) -> Path:
    path = Path(repo_root).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"repo root does not exist: {path}")
    if not SKILL_HOST_PATH.exists():
        raise FileNotFoundError(f"missing skill-bundled runtime adapter: {SKILL_HOST_PATH}")
    return path


def _load_skill_host():
    spec = importlib.util.spec_from_file_location("prompt_workflow_skill_host", SKILL_HOST_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to create module spec for {SKILL_HOST_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json_object(
    path: Path,
    *,
    required_fields: set[str],
    max_bytes: int,
) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"input file does not exist: {path}")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    try:
        with path.open("rb") as input_file:
            raw_payload = input_file.read(max_bytes + 1)
        if len(raw_payload) > max_bytes:
            raise ValueError(f"input file exceeds {max_bytes} bytes: {path}")
        payload = json.loads(raw_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"input payload must be an object: {path}")
    missing = sorted(required_fields - set(payload.keys()))
    if missing:
        raise ValueError(f"input payload missing required fields: {', '.join(missing)}")
    return payload


def _validate_command_host_io_paths(repo_root: Path, args: argparse.Namespace, response_file: Path) -> None:
    if args.allow_unsafe_host_io_paths:
        return

    _validate_host_io_file(repo_root, response_file, field_name="response-file", is_response_file=True)

    if args.command == "start":
        _validate_host_io_file(repo_root, Path(args.request_file), field_name="request-file")
        return

    if args.command == "resume":
        _validate_host_io_file(repo_root, Path(args.observation_file), field_name="observation-file")


def _validate_host_io_file(
    repo_root: Path,
    path: Path,
    *,
    field_name: str,
    is_response_file: bool = False,
) -> None:
    if host_io.is_host_io_path(repo_root, path):
        return

    message = (
        f"{field_name} must be under {host_io.host_io_root(repo_root)}; "
        "allocate paths with scripts/host_io.py or pass --allow-unsafe-host-io-paths for debugging"
    )
    if is_response_file:
        raise UnsafeResponseFilePathError(message)
    raise UnsafeHostIoPathError(message)


def _validate_start_response(response: dict) -> None:
    if not isinstance(response, dict):
        raise ValueError("adapter response must be an object")
    kind = response.get("kind")
    if kind not in {"yield", "done", "blocked"}:
        raise ValueError("start response kind must be 'yield', 'done', or 'blocked'")


def _validate_resume_response(response: dict) -> None:
    if not isinstance(response, dict):
        raise ValueError("adapter response must be an object")
    kind = response.get("kind")
    if kind not in {"yield", "done"}:
        raise ValueError("resume response kind must be 'yield' or 'done'")


def _validate_preflight_response(response: dict) -> None:
    if not isinstance(response, dict):
        raise ValueError("preflight response must be an object")
    if response.get("kind") != "preflight_result":
        raise ValueError("preflight response kind must be 'preflight_result'")


def _print_success_status(response: dict, response_file: Path) -> None:
    kind = response["kind"]
    if kind in {"yield", "done"}:
        print(
            f"status={kind} run_id={response['run_id']} "
            f"step_id={response['step_id']} response_file={response_file}"
        )
        return
    if kind == "blocked":
        print(
            f"status=blocked workflow_id={response.get('workflow_id', '')} "
            f"reason={response.get('blocked_reason', '')} response_file={response_file}"
        )
        return
    print(
        f"status=preflight workflow_id={response.get('workflow_id', '')} "
        f"preflight_status={response.get('status', '')} response_file={response_file}"
    )


def _write_json_atomic(path: Path, payload: dict) -> None:
    host_io._write_json_atomic(path, payload)


def _handle_error(exc: Exception, response_file: Path) -> int:
    module_name = exc.__class__.__name__
    if module_name == "BootstrapError":
        error_type = "bootstrap_error"
        exit_code = ERROR_EXIT_CODES["bootstrap_error"]
    elif module_name == "ProtocolError":
        error_type = "protocol_error"
        exit_code = ERROR_EXIT_CODES["protocol_error"]
    elif module_name == "ObservationValidationError":
        error_type = "validation_error"
        exit_code = ERROR_EXIT_CODES["observation_validation_error"]
    elif module_name == "SchemaValidationError":
        error_type = "validation_error"
        exit_code = ERROR_EXIT_CODES["input_error"]
    elif module_name == "RequestValidationError":
        error_type = "validation_error"
        exit_code = ERROR_EXIT_CODES["input_error"]
    elif module_name == "WorkflowExecutionError":
        error_type = "execution_error"
        exit_code = ERROR_EXIT_CODES["execution_error"]
    elif isinstance(exc, UnsafeHostIoPathError):
        error_type = "validation_error"
        exit_code = ERROR_EXIT_CODES["input_error"]
    elif isinstance(exc, (FileNotFoundError, ValueError)):
        error_type = "io_error" if isinstance(exc, FileNotFoundError) else "validation_error"
        exit_code = ERROR_EXIT_CODES["input_error"]
    else:
        error_type = "execution_error"
        exit_code = ERROR_EXIT_CODES["execution_error"]

    error_payload = {
        "kind": "error",
        "error_type": error_type,
        "message": str(exc),
        "details": _error_details(exc),
    }
    error_code = getattr(exc, "code", None)
    if isinstance(error_code, str) and error_code.strip():
        error_payload["code"] = error_code
    if isinstance(exc, UnsafeResponseFilePathError):
        print(f"status=error error_type={error_type} response_file=")
        print(str(exc), file=sys.stderr)
        return exit_code

    try:
        _write_json_atomic(response_file, error_payload)
    except Exception as write_exc:  # pragma: no cover - secondary failure path
        print(f"failed to write response file: {write_exc}", file=sys.stderr)
        return ERROR_EXIT_CODES["response_write_error"]

    print(f"status=error error_type={error_type} response_file={response_file}")
    print(str(exc), file=sys.stderr)
    return exit_code


def _error_details(exc: Exception) -> dict:
    details: dict[str, object] = {}
    for field_name in ("path", "expected", "actual", "source", "repairable"):
        value = getattr(exc, field_name, None)
        if value is not None:
            details[field_name] = value
    return details


if __name__ == "__main__":
    raise SystemExit(main())
