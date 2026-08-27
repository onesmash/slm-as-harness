"""Quote-in-place citation checks for Co-STORM report artifacts.

Kept outside verifiers.py so custom requirement functions can import a stable
helper instead of adding same-file helper layers.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_MAX_SAFE_REPO_TEXT_BYTES = 512 * 1024

_REGISTRY_ROW = re.compile(r"^\s*\[(\d+)\]\s*(.+?)\s*$")
_MARKER = re.compile(r"\[(\d+)\]")
_LOCATOR_WINDOW = 200


def parse_registry_locators(evidence_registry: object) -> dict[int, str] | str:
    if not isinstance(evidence_registry, list) or not evidence_registry:
        return "evidence_registry is missing from persisted state"
    locators: dict[int, str] = {}
    for entry in evidence_registry:
        if not isinstance(entry, str):
            return "evidence_registry entries must be strings"
        match = _REGISTRY_ROW.match(entry)
        if match is None:
            return "every evidence_registry entry must contain a citation identifier and grounded details"
        evidence_id = int(match.group(1))
        remainder = match.group(2).strip()
        locator = remainder.split(" — ", 1)[0].strip()
        if not locator:
            return f"evidence_registry [{evidence_id}] is missing a source locator"
        if evidence_id in locators:
            return "evidence_registry contains duplicate citation identifiers"
        locators[evidence_id] = locator
    return locators


def missing_in_place_locator(report_text: str, evidence_registry: object) -> str | None:
    locators = parse_registry_locators(evidence_registry)
    if isinstance(locators, str):
        return locators
    visible = re.sub(r"<!--.*?-->", "", report_text, flags=re.DOTALL)
    matches = list(_MARKER.finditer(visible))
    if not matches:
        return "report must contain at least one numeric inline citation"
    for match in matches:
        evidence_id = int(match.group(1))
        locator = locators.get(evidence_id)
        if locator is None:
            return f"report contains citation identifiers absent from evidence_registry: [{evidence_id}]"
        start = max(0, match.start() - _LOCATOR_WINDOW)
        end = min(len(visible), match.end() + _LOCATOR_WINDOW)
        if locator not in visible[start:end]:
            return (
                f"report citation [{evidence_id}] is missing in-place source locator {locator!r}"
            )
    return None


def resolve_safe_repo_file(repo_root: str, raw_path: object) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    try:
        repo = Path(repo_root).expanduser().resolve()
        normalized = raw_path
        if (
            normalized != normalized.strip()
            or "\\" in normalized
            or any(ord(char) < 32 for char in normalized)
            or normalized.startswith("/")
            or re.match(r"^[A-Za-z]:/", normalized)
        ):
            return None
        parts = normalized.split("/")
        if any(part in ("", ".", "..") for part in parts):
            return None
        candidate = repo.joinpath(*parts)
        resolved = candidate.resolve(strict=False)
        relative = resolved.relative_to(repo)
        current = repo
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return None
        if resolved.is_symlink() or not resolved.is_file():
            return None
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def load_utf8_report(repo_root: str, raw_path: object) -> tuple[str | None, str | None]:
    """Return (report_text, None) or (None, error_message) for a repo-relative file."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "report_path is missing"
    candidate = resolve_safe_repo_file(repo_root, raw_path)
    if candidate is None:
        return None, "report_path must point to a readable repository-relative regular report file"
    file_descriptor = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        file_descriptor = os.open(str(candidate), flags)
        with os.fdopen(file_descriptor, "rb") as handle:
            file_descriptor = None
            data = handle.read(_MAX_SAFE_REPO_TEXT_BYTES + 1)
            if len(data) > _MAX_SAFE_REPO_TEXT_BYTES:
                return None, "report file could not be read as UTF-8"
            return data.decode("utf-8"), None
    except (OSError, UnicodeError):
        return None, "report file could not be read as UTF-8"
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
