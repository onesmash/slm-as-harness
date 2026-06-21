from __future__ import annotations

import shutil
from pathlib import Path


SHORTCUTS_DIRNAME = "workflow-shortcuts"


def ensure_workflow_shortcut_skill(
    *,
    runtime_skill_root: str | Path,
    workflow_id: str,
) -> dict[str, str]:
    runtime_root = Path(runtime_skill_root).expanduser().resolve()
    shortcuts_root = runtime_root / SHORTCUTS_DIRNAME
    target_dir = shortcuts_root / workflow_id
    temp_dir = shortcuts_root / f".{workflow_id}.shortcut-tmp"
    backup_dir = shortcuts_root / f".{workflow_id}.shortcut-backup"
    skill_name = workflow_shortcut_skill_name(workflow_id)
    skill_file = target_dir / "SKILL.md"

    _remove_path(temp_dir)
    _remove_path(backup_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "SKILL.md").write_text(
        _render_workflow_shortcut_skill(workflow_id),
        encoding="utf-8",
    )

    try:
        if target_dir.exists():
            target_dir.replace(backup_dir)
        temp_dir.replace(target_dir)
        _remove_path(backup_dir)
    except Exception:
        _remove_path(target_dir)
        if backup_dir.exists():
            backup_dir.replace(target_dir)
        raise
    finally:
        _remove_path(temp_dir)

    return {
        "shortcut_skill_name": skill_name,
        "shortcut_skill_dir": str(target_dir),
        "shortcut_skill_file": str(skill_file),
    }


def delete_workflow_shortcut_skill(
    *,
    runtime_skill_root: str | Path,
    workflow_id: str,
) -> dict[str, str | bool | None]:
    runtime_root = Path(runtime_skill_root).expanduser().resolve()
    target_dir = runtime_root / SHORTCUTS_DIRNAME / workflow_id
    backup_dir = target_dir.parent / f".{workflow_id}.shortcut-delete-backup"
    skill_name = workflow_shortcut_skill_name(workflow_id)
    skill_file = target_dir / "SKILL.md"

    if not target_dir.exists():
        return {
            "shortcut_skill_name": skill_name,
            "shortcut_skill_dir": str(target_dir),
            "shortcut_skill_file": str(skill_file),
            "removed_shortcut_skill": False,
        }

    _remove_path(backup_dir)
    try:
        target_dir.replace(backup_dir)
        _remove_path(backup_dir)
    except Exception:
        if not target_dir.exists() and backup_dir.exists():
            backup_dir.replace(target_dir)
        raise

    return {
        "shortcut_skill_name": skill_name,
        "shortcut_skill_dir": str(target_dir),
        "shortcut_skill_file": str(skill_file),
        "removed_shortcut_skill": True,
    }


def workflow_shortcut_skill_name(workflow_id: str) -> str:
    return f"workflow:{workflow_id}"


def _render_workflow_shortcut_skill(workflow_id: str) -> str:
    skill_name = workflow_shortcut_skill_name(workflow_id)
    slash_name = f"/{skill_name}"
    return f"""---
name: {skill_name}
description: |
  Slash-only shortcut for durable workflow `{workflow_id}`. Load only when the
  user explicitly invokes `{slash_name}`, then continue through
  `/durable-workflow-runtime {workflow_id}` followed by the user's raw trailing
  text.
---

/durable-workflow-runtime {workflow_id} followed by the user's raw trailing text after `{slash_name}`
"""


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    if path.exists():
        shutil.rmtree(path)
