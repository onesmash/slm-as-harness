from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SETUP_SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_SKILL_ROOT = SETUP_SKILL_ROOT.parent
RUNTIME_SCRIPTS_ROOT = DEFAULT_RUNTIME_SKILL_ROOT / "scripts"

if str(RUNTIME_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SCRIPTS_ROOT))

from workflow_shortcut_skill import (  # noqa: E402
    DEFAULT_GLOBAL_SKILL_ROOTS,
    install_global_workflow_shortcut_skills,
)


class SetupError(ValueError):
    pass


def setup_workflow_shortcuts(
    *,
    runtime_skill_root: str | Path,
    skill_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    runtime_root = _resolve_runtime_skill_root(runtime_skill_root)
    try:
        return install_global_workflow_shortcut_skills(
            runtime_skill_root=runtime_root,
            skill_roots=skill_roots,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError, OSError) as exc:
        raise SetupError(str(exc)) from exc


def _resolve_runtime_skill_root(runtime_skill_root: str | Path) -> Path:
    path = Path(runtime_skill_root).expanduser().resolve()
    required_paths = [
        path / "workflow-binding.json",
        path / "workflow-runtime",
        path / "workflow-runtime" / "workflows",
        path / "workflow-shortcuts",
    ]
    missing = [str(item) for item in required_paths if not item.exists()]
    if missing:
        raise SetupError(f"missing durable-workflow-runtime paths: {', '.join(missing)}")
    return path


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = setup_workflow_shortcuts(
            runtime_skill_root=args.runtime_skill_root,
            skill_roots=args.skill_root,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install workflow-shortcuts skills into ~/.agents/skills and ~/.claude/skills"
        )
    )
    parser.add_argument("--runtime-skill-root", default=str(DEFAULT_RUNTIME_SKILL_ROOT))
    parser.add_argument(
        "--skill-root",
        action="append",
        help=(
            "Global skill directory to receive shortcut symlinks. Repeatable. "
            f"Defaults to {DEFAULT_GLOBAL_SKILL_ROOTS[0]} and {DEFAULT_GLOBAL_SKILL_ROOTS[1]}."
        ),
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
