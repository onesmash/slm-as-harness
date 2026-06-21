from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


INJECT_SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_SKILL_ROOT = INJECT_SKILL_ROOT.parent
DEFAULT_TARGET_FILES = ("AGENTS.md", "CLAUDE.md")
START_MARKER = "<!-- durable-workflow-runtime:start -->"
END_MARKER = "<!-- durable-workflow-runtime:end -->"
_SAFE_RELATIVE_TARGET_PATTERN = re.compile(r"^[^:\0]+$")


class InjectError(ValueError):
    pass


def inject_workflow_instructions(
    *,
    runtime_skill_root: str | Path,
    repo_root: str | Path,
    target_files: list[str] | None = None,
) -> dict[str, Any]:
    runtime_root = _resolve_runtime_skill_root(runtime_skill_root)
    repo_path = _resolve_repo_root(repo_root)
    targets = target_files or list(DEFAULT_TARGET_FILES)
    binding_payload = _load_json_object(runtime_root / "workflow-binding.json")
    workflows = _load_workflow_catalog(binding_payload)
    block = _render_block(workflows)

    updated_files = []
    for target_file in targets:
        target_path = _resolve_target_file(repo_path, target_file)
        action = _write_or_replace_block(target_path, block)
        updated_files.append(
            {
                "path": str(target_path),
                "action": action,
            }
        )

    return {
        "kind": "workflow_instruction_injection",
        "workflow_count": len(workflows),
        "updated_files": updated_files,
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
        raise InjectError(f"missing durable-workflow-runtime paths: {', '.join(missing)}")
    return path


def _resolve_repo_root(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve()
    if not path.exists():
        raise InjectError(f"repo root does not exist: {path}")
    if not path.is_dir():
        raise InjectError(f"repo root must be a directory: {path}")
    return path


def _resolve_target_file(repo_root: Path, target_file: str) -> Path:
    if not isinstance(target_file, str) or not target_file.strip():
        raise InjectError("target file must be a non-empty relative path")
    if not _SAFE_RELATIVE_TARGET_PATTERN.fullmatch(target_file):
        raise InjectError(f"target file contains unsupported characters: {target_file}")
    relative_path = Path(target_file)
    if relative_path.is_absolute() or any(part in {"", ".", ".."} for part in relative_path.parts):
        raise InjectError(f"target file must be a safe relative path: {target_file}")
    return repo_root / relative_path


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise InjectError(f"missing workflow binding config: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InjectError(f"invalid workflow binding config JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise InjectError("workflow binding config must be a JSON object")
    return payload


def _load_workflow_catalog(binding_payload: dict[str, Any]) -> list[dict[str, str]]:
    workflows = binding_payload.get("workflows")
    if not isinstance(workflows, list):
        raise InjectError("workflow binding config field 'workflows' must be a list")

    catalog: list[dict[str, str]] = []
    for item in workflows:
        if not isinstance(item, dict):
            continue
        workflow_id = item.get("workflow_id")
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            continue
        description = item.get("flow_description")
        if not isinstance(description, str) or not description.strip():
            description = "No description provided."
        catalog.append(
            {
                "workflow_id": workflow_id.strip(),
                "description": description.strip(),
            }
        )
    if not catalog:
        raise InjectError("workflow binding config does not publish any workflows")
    return catalog


def _render_block(workflows: list[dict[str, str]]) -> str:
    lines = [
        START_MARKER,
        "How to use durable-workflow-runtime:",
        "- When the user's task matches one of the workflows below, use `durable-workflow-runtime` instead of manually orchestrating the process in chat.",
        "- Select a workflow by matching the user's request against `<workflow_id>` and `<description>` in `<available_workflows>`; if no workflow clearly matches, ask the user to choose.",
        "- Invocation format: `durable-workflow-runtime <workflow_id> <user_prompt>`.",
        "Available workflows:",
        "<available_workflows>",
    ]
    for workflow in workflows:
        workflow_id = html.escape(workflow["workflow_id"], quote=False)
        description = html.escape(workflow["description"], quote=False)
        lines.extend(
            [
                "  <workflow>",
                f"    <workflow_id>{workflow_id}</workflow_id>",
                f"    <description>{description}</description>",
                "  </workflow>",
            ]
        )
    lines.extend(
        [
            "</available_workflows>",
            END_MARKER,
        ]
    )
    return "\n".join(lines) + "\n"


def _write_or_replace_block(path: Path, block: str) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(block, encoding="utf-8")
        return "created"

    text = path.read_text(encoding="utf-8")
    start_count = text.count(START_MARKER)
    end_count = text.count(END_MARKER)
    if start_count != end_count:
        raise InjectError(f"mismatched durable-workflow-runtime markers in {path}")
    if start_count > 1:
        raise InjectError(f"multiple durable-workflow-runtime marker blocks in {path}")
    if start_count == 1:
        start_index = text.index(START_MARKER)
        end_index = text.index(END_MARKER, start_index) + len(END_MARKER)
        replacement = _with_surrounding_newlines(text, start_index, end_index, block)
        path.write_text(text[:start_index] + replacement + text[end_index:], encoding="utf-8")
        return "replaced"

    prefix = text if not text or text.endswith("\n") else text + "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    path.write_text(prefix + block, encoding="utf-8")
    return "appended"


def _with_surrounding_newlines(text: str, start_index: int, end_index: int, block: str) -> str:
    prefix = "\n" if start_index > 0 and not text[:start_index].endswith("\n") else ""
    suffix = "\n" if end_index < len(text) and not text[end_index:].startswith("\n") else ""
    return prefix + block.rstrip("\n") + suffix


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = inject_workflow_instructions(
            runtime_skill_root=args.runtime_skill_root,
            repo_root=args.repo_root,
            target_files=args.target_file,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inject durable-workflow-runtime workflow instructions into agent files"
    )
    parser.add_argument("--runtime-skill-root", default=str(DEFAULT_RUNTIME_SKILL_ROOT))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--target-file", action="append")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
