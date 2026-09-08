from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


SHORTCUTS_DIRNAME = "workflow-shortcuts"
CLAUDE_SKILLS_DIRNAME = ".claude/skills"
DEFAULT_GLOBAL_SKILL_ROOTS = (
    Path.home() / ".agents" / "skills",
    Path.home() / ".claude" / "skills",
)


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


def list_workflow_shortcut_skills(runtime_skill_root: str | Path) -> list[Path]:
    runtime_root = Path(runtime_skill_root).expanduser().resolve()
    shortcuts_root = runtime_root / SHORTCUTS_DIRNAME
    if not shortcuts_root.exists():
        raise FileNotFoundError(f"missing workflow-shortcuts directory: {shortcuts_root}")
    if not shortcuts_root.is_dir():
        raise NotADirectoryError(f"workflow-shortcuts must be a directory: {shortcuts_root}")

    shortcuts: list[Path] = []
    for child in sorted(shortcuts_root.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_dir() and (child / "SKILL.md").is_file():
            shortcuts.append(child)
    return shortcuts


def install_global_workflow_shortcut_skills(
    *,
    runtime_skill_root: str | Path,
    skill_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    runtime_root = Path(runtime_skill_root).expanduser().resolve()
    shortcuts_root = runtime_root / SHORTCUTS_DIRNAME
    shortcuts = list_workflow_shortcut_skills(runtime_root)
    shortcut_ids = {path.name for path in shortcuts}
    resolved_skill_roots = _resolve_skill_roots(skill_roots)

    links: list[dict[str, Any]] = []
    for source_dir in shortcuts:
        targets = []
        for skill_root in resolved_skill_roots:
            link_path = skill_root / source_dir.name
            action = _ensure_shortcut_symlink(source_dir=source_dir, link_path=link_path)
            targets.append({"path": str(link_path), "action": action})
        links.append(
            {
                "workflow_id": source_dir.name,
                "source": str(source_dir),
                "targets": targets,
            }
        )

    pruned = _prune_stale_shortcut_links(
        skill_roots=resolved_skill_roots,
        shortcuts_root=shortcuts_root,
        current_shortcut_ids=shortcut_ids,
    )

    return {
        "kind": "workflow_shortcut_setup",
        "runtime_skill_root": str(runtime_root),
        "shortcuts_root": str(shortcuts_root),
        "shortcut_count": len(shortcuts),
        "skill_roots": [str(path) for path in resolved_skill_roots],
        "links": links,
        "pruned": pruned,
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


def _resolve_skill_roots(skill_roots: list[str | Path] | None) -> list[Path]:
    roots = skill_roots if skill_roots else list(DEFAULT_GLOBAL_SKILL_ROOTS)
    resolved: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        path = Path(root).expanduser().resolve()
        if path in seen:
            continue
        seen.add(path)
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise NotADirectoryError(f"skill root must be a directory: {path}")
        resolved.append(path)
    return resolved


def _ensure_shortcut_symlink(*, source_dir: Path, link_path: Path) -> str:
    source = source_dir.expanduser().resolve()
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.is_symlink():
        if link_path.resolve(strict=False) == source:
            return "unchanged"
        link_path.unlink()
        link_path.symlink_to(source, target_is_directory=True)
        return "replaced"
    if link_path.exists():
        raise ValueError(
            f"cannot create shortcut because a non-symlink path already exists: {link_path}"
        )
    link_path.symlink_to(source, target_is_directory=True)
    return "created"


def _prune_stale_shortcut_links(
    *,
    skill_roots: list[Path],
    shortcuts_root: Path,
    current_shortcut_ids: set[str],
) -> list[dict[str, str]]:
    shortcuts_root = shortcuts_root.expanduser().resolve()
    stale_links: list[Path] = []
    for skill_root in skill_roots:
        if not skill_root.exists():
            continue
        for child in sorted(skill_root.iterdir()):
            if child.name.startswith(".") or child.name in current_shortcut_ids:
                continue
            if not child.is_symlink():
                continue
            if not _symlink_points_into(child, shortcuts_root):
                continue
            stale_links.append(child)

    pruned: list[dict[str, str]] = []
    for child in stale_links:
        child.unlink()
        pruned.append(
            {
                "path": str(child),
                "reason": "stale shortcut pointing at this runtime",
            }
        )
    return pruned


def _symlink_points_into(link_path: Path, directory: Path) -> bool:
    raw_target = Path(os.readlink(link_path))
    if not raw_target.is_absolute():
        raw_target = link_path.parent / raw_target
    resolved = raw_target.resolve(strict=False)
    try:
        resolved.relative_to(directory)
        return True
    except ValueError:
        return False


def _ensure_claude_shortcut_entry(*, target_dir: Path, claude_shortcut_dir: Path) -> bool:
    action = _ensure_shortcut_symlink(source_dir=target_dir, link_path=claude_shortcut_dir)
    return action != "unchanged"


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
