from __future__ import annotations

import shutil
from pathlib import Path


SHORTCUTS_DIRNAME = "workflow-shortcuts"
CLAUDE_SKILLS_DIRNAME = ".claude/skills"


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
    claude_skills_root = runtime_root / CLAUDE_SKILLS_DIRNAME
    claude_shortcut_dir = claude_skills_root / workflow_id

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
        created_claude_shortcut_skill = _ensure_claude_shortcut_entry(
            target_dir=target_dir,
            claude_shortcut_dir=claude_shortcut_dir,
        )
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
        "claude_shortcut_skill_dir": str(claude_shortcut_dir.resolve(strict=False)),
        "created_claude_shortcut_skill": created_claude_shortcut_skill,
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
    claude_shortcut_dir = runtime_root / CLAUDE_SKILLS_DIRNAME / workflow_id

    if not target_dir.exists():
        return {
            "shortcut_skill_name": skill_name,
            "shortcut_skill_dir": str(target_dir),
            "shortcut_skill_file": str(skill_file),
            "claude_shortcut_skill_dir": str(claude_shortcut_dir.resolve(strict=False)),
            "removed_shortcut_skill": False,
            "removed_claude_shortcut_skill": _remove_claude_shortcut_entry(
                target_dir=target_dir,
                claude_shortcut_dir=claude_shortcut_dir,
            ),
        }

    _remove_path(backup_dir)
    try:
        target_dir.replace(backup_dir)
        removed_claude_shortcut_skill = _remove_claude_shortcut_entry(
            target_dir=backup_dir,
            claude_shortcut_dir=claude_shortcut_dir,
        )
        _remove_path(backup_dir)
    except Exception:
        if not target_dir.exists() and backup_dir.exists():
            backup_dir.replace(target_dir)
        raise

    return {
        "shortcut_skill_name": skill_name,
        "shortcut_skill_dir": str(target_dir),
        "shortcut_skill_file": str(skill_file),
        "claude_shortcut_skill_dir": str(claude_shortcut_dir.resolve(strict=False)),
        "removed_shortcut_skill": True,
        "removed_claude_shortcut_skill": removed_claude_shortcut_skill,
    }


def workflow_shortcut_skill_name(workflow_id: str) -> str:
    return workflow_id


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


def _ensure_claude_shortcut_entry(*, target_dir: Path, claude_shortcut_dir: Path) -> bool:
    claude_shortcut_dir.parent.mkdir(parents=True, exist_ok=True)
    if claude_shortcut_dir.is_symlink():
        if claude_shortcut_dir.resolve() == target_dir.resolve():
            return False
        claude_shortcut_dir.unlink()
    elif claude_shortcut_dir.exists():
        raise ValueError(
            f"cannot create Claude shortcut because a non-symlink path already exists: {claude_shortcut_dir}"
        )
    claude_shortcut_dir.symlink_to(target_dir, target_is_directory=True)
    return True


def _remove_claude_shortcut_entry(*, target_dir: Path, claude_shortcut_dir: Path) -> bool:
    if not claude_shortcut_dir.exists() and not claude_shortcut_dir.is_symlink():
        return False
    if claude_shortcut_dir.is_symlink():
        claude_shortcut_dir.unlink(missing_ok=True)
        return True
    return False


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    if path.exists():
        shutil.rmtree(path)
