"""Evidence-index citation checks for Co-STORM report artifacts.

Kept outside verifiers.py so custom requirement functions can import a stable
helper instead of adding same-file helper layers.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_MAX_SAFE_REPO_TEXT_BYTES = 512 * 1024
_MAX_SAFE_REPO_PATH_BYTES = 2048
_MAX_CITATION_ID_DIGITS = 6
# Minimum locator length before the "repeated in report body" rejection applies,
# so short or common tokens do not produce false positives.
_MIN_REPEAT_LOCATOR_LENGTH = 4

_REGISTRY_ROW = re.compile(r"^[ \t]*\[([0-9]+)\][ \t]*(.+?)[ \t]*$")
_MARKER = re.compile(r"\[([0-9]+)\]")
_INDEX_HEADING = re.compile(
    r"(?im)^[ ]{0,3}##[ \t]+(?:[0-9]+\.[ \t]*)?(?:Evidence index|证据索引)[ \t]*$"
)
_SECTION_HEADING = re.compile(r"(?im)^[ ]{0,3}(##)[ \t]+(.+?)[ \t]*$")
_INDEX_ROW = re.compile(r"^[ ]{0,3}-[ \t]+\[([0-9]+)\][ \t]+(.+?)[ \t]*$")
_FENCE_OPEN = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
_HTML_BLOCK_OPEN = re.compile(
    r"^[ ]{0,3}<(?P<tag>[A-Za-z][A-Za-z0-9:-]*)(?:[ \t/>]|$)",
    re.IGNORECASE,
)
_HTML_BLOCK_CLOSE = re.compile(
    r"^[ ]{0,3}</(?P<tag>[A-Za-z][A-Za-z0-9:-]*)[ \t]*>",
    re.IGNORECASE,
)
# HTML void elements are self-contained and must not open a raw-HTML block.
_HTML_VOID_ELEMENTS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _blank_non_newline(text: str) -> str:
    return "".join("\n" if char == "\n" else " " for char in text)


def _mask_html_comments(text: str) -> tuple[str, str | None]:
    chars = list(text)
    cursor = 0
    while True:
        start = text.find("<!--", cursor)
        if start < 0:
            return "".join(chars), None
        end = text.find("-->", start + 4)
        if end < 0:
            return "".join(chars), "report contains an unclosed HTML comment"
        for index in range(start, end + 3):
            if text[index] != "\n":
                chars[index] = " "
        cursor = end + 3


def _is_fence_close(line: str, marker: str) -> bool:
    char = re.escape(marker[0])
    return re.fullmatch(rf"[ ]{{0,3}}{char}{{{len(marker)},}}[ \t]*", line) is not None


def _mask_markdown_blocks(text: str) -> tuple[str, str | None]:
    masked_lines: list[str] = []
    active_fence: str | None = None
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\n")
        if active_fence is not None:
            masked_lines.append(_blank_non_newline(raw_line))
            if _is_fence_close(line, active_fence):
                active_fence = None
            continue
        opening = _FENCE_OPEN.match(line)
        if opening is not None:
            active_fence = opening.group(1)
            masked_lines.append(_blank_non_newline(raw_line))
            continue
        if re.match(r"^(?: {4}|\t)", line):
            masked_lines.append(_blank_non_newline(raw_line))
            continue
        masked_lines.append(raw_line)
    masked = "".join(masked_lines)
    if active_fence is not None:
        return masked, "report contains an unclosed fenced code block"
    return masked, None


def _mask_raw_html_blocks(text: str) -> tuple[str, str | None]:
    masked_lines: list[str] = []
    active_tag: str | None = None
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\n")
        if active_tag is not None:
            masked_lines.append(_blank_non_newline(raw_line))
            if re.search(rf"</{re.escape(active_tag)}[ \t]*>", line, re.IGNORECASE):
                active_tag = None
            continue
        opening = _HTML_BLOCK_OPEN.match(line)
        if opening is not None:
            tag = opening.group("tag")
            masked_lines.append(_blank_non_newline(raw_line))
            if tag.casefold() in _HTML_VOID_ELEMENTS:
                continue
            if not re.search(rf"</{re.escape(tag)}[ \t]*>", line, re.IGNORECASE) and not re.search(
                r"/[ \t]*>[ \t]*$",
                line,
            ):
                active_tag = tag
            continue
        if _HTML_BLOCK_CLOSE.match(line) is not None:
            masked_lines.append(_blank_non_newline(raw_line))
            continue
        masked_lines.append(raw_line)
    masked = "".join(masked_lines)
    if active_tag is not None:
        return masked, "report contains an unclosed raw HTML block"
    return masked, None


def _mask_inline_code(text: str) -> tuple[str, str | None]:
    chars = list(text)
    cursor = 0
    while cursor < len(text):
        if text[cursor] != "`" or (cursor > 0 and text[cursor - 1] == "\\"):
            cursor += 1
            continue
        start = cursor
        while cursor < len(text) and text[cursor] == "`":
            cursor += 1
        delimiter = text[start:cursor]
        end = text.find(delimiter, cursor)
        if end < 0:
            return "".join(chars), "report contains an unclosed inline code span"
        for index in range(start, end + len(delimiter)):
            if text[index] != "\n":
                chars[index] = " "
        cursor = end + len(delimiter)
    return "".join(chars), None


def _parse_marker_ids(text: str) -> tuple[set[int] | None, str | None]:
    marker_ids: set[int] = set()
    for match in _MARKER.finditer(text):
        raw_id = match.group(1)
        if len(raw_id) > _MAX_CITATION_ID_DIGITS:
            return None, "citation identifier exceeds the supported size"
        marker_ids.add(int(raw_id))
    return marker_ids, None


def extract_citation_ids(report_text: str) -> tuple[set[int] | None, str | None]:
    """Extract citation ids from rendered Markdown without executing code."""
    rendered, error = rendered_report_text(report_text)
    if error is not None:
        return None, error
    if rendered is None:
        return None, "report could not be rendered"
    return _parse_marker_ids(rendered)


def rendered_report_text(report_text: str) -> tuple[str | None, str | None]:
    """Return visible Markdown text with executable/hidden regions masked."""
    normalized = _normalize_newlines(report_text)
    visible, error = _mask_html_comments(normalized)
    if error is not None:
        return None, error
    visible, error = _mask_raw_html_blocks(visible)
    if error is not None:
        return None, error
    visible, error = _mask_markdown_blocks(visible)
    if error is not None:
        return None, error
    visible, error = _mask_inline_code(visible)
    if error is not None:
        return None, error
    return visible, None


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
        raw_id = match.group(1)
        if len(raw_id) > _MAX_CITATION_ID_DIGITS:
            return "evidence_registry citation identifiers exceed the supported size"
        evidence_id = int(raw_id)
        remainder = match.group(2).strip()
        locator = remainder.split(" — ", 1)[0].strip()
        if not locator:
            return f"evidence_registry [{evidence_id}] is missing a source locator"
        if evidence_id in locators:
            return "evidence_registry contains duplicate citation identifiers"
        locators[evidence_id] = locator
    return locators


# ---------------------------------------------------------------------------
# Workflow shared format contracts: expert roster / evidence registry / new
# evidence items. Single source of truth for the Co-STORM wire format so the
# warm-start, launch, and Moderator verifiers cannot drift apart.
# ---------------------------------------------------------------------------

EXPERT_ROSTER_REQUIRED_KEYS = frozenset({"id", "role", "brief"})

_NEW_EVIDENCE_SEPARATOR = " — "


def expert_roster_entry_format_error(entry: object) -> str | None:
    """Return a format error for one expert roster entry, or None when valid.

    A valid entry is an object with exactly the keys id, role, and brief, all
    non-empty trimmed strings.
    """
    if not isinstance(entry, dict):
        return "must be an object with exactly id, role, and brief"
    if set(entry) != EXPERT_ROSTER_REQUIRED_KEYS:
        return "must contain exactly id, role, and brief"
    for field_name in ("id", "role", "brief"):
        value = entry.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return f"{field_name} must be a non-empty string"
    return None


def registry_entry_parts(entry: object) -> tuple[int, str] | None:
    """Return (evidence_id, remainder) for a valid '[n] ...' registry row."""
    if not isinstance(entry, str):
        return None
    match = _REGISTRY_ROW.match(entry)
    if match is None:
        return None
    raw_id = match.group(1)
    if len(raw_id) > _MAX_CITATION_ID_DIGITS:
        return None
    return int(raw_id), match.group(2).strip()


def evidence_registry_entry_format_error(entry: object) -> str | None:
    """Return a format error for one evidence registry row, or None when valid.

    A valid row is '[<id>] <locator>' with a bounded numeric id and a non-empty
    locator; an optional ' — <claim>' suffix, when present, must itself be
    non-empty. Locator-only rows stay valid, matching parse_registry_locators.
    """
    if not isinstance(entry, str) or not entry.strip():
        return "must be a non-empty string in '[n] locator' form"
    match = _REGISTRY_ROW.match(entry)
    if match is None:
        return "must contain a citation identifier and claim in '[n] locator — claim' form"
    raw_id = match.group(1)
    if len(raw_id) > _MAX_CITATION_ID_DIGITS:
        return "has an oversized citation identifier"
    detail = match.group(2).strip()
    if not detail:
        return "must contain a non-empty claim"
    if detail.startswith("\u2014"):
        return "must contain a non-empty source locator"
    if _NEW_EVIDENCE_SEPARATOR in detail:
        _, _, claim = detail.partition(_NEW_EVIDENCE_SEPARATOR)
        if not claim.strip():
            return "must include a non-empty claim after the locator separator"
    elif detail.endswith(" —") or detail.endswith("\u2014"):
        return "must include a non-empty claim after the locator separator"
    return None


def new_evidence_item_format_error(item: object) -> str | None:
    """Return a format error for one expert new-evidence item, or None when valid.

    A valid item is 'locator — claim' with both sides non-empty and no [n]
    citation markers; global citation numbering is owned by
    launch_expert_subagents.
    """
    if not isinstance(item, str) or not item.strip():
        return "must be a non-empty string in 'locator — claim' form"
    stripped = item.strip()
    if _MARKER.search(stripped):
        return "must not contain citation markers"
    if _NEW_EVIDENCE_SEPARATOR not in stripped:
        return "must use the form 'locator — claim'"
    locator, claim = stripped.split(_NEW_EVIDENCE_SEPARATOR, 1)
    if not locator.strip() or not claim.strip():
        return "must include a non-empty locator and claim"
    return None


def source_locator_key(text: str) -> str:
    """Normalize a locator-bearing string for cross-checking and deduplication.

    The locator is the text before the ' — ' separator, casefolded; text without
    the separator is trimmed and casefolded as-is.
    """
    normalized = text.strip()
    if _NEW_EVIDENCE_SEPARATOR in normalized:
        normalized = normalized.split(_NEW_EVIDENCE_SEPARATOR, 1)[0].strip()
    return normalized.casefold()


def missing_evidence_index(report_text: str, evidence_registry: object) -> str | None:
    locators = parse_registry_locators(evidence_registry)
    if isinstance(locators, str):
        return locators
    normalized = _normalize_newlines(report_text)
    visible, error = _mask_html_comments(normalized)
    if error is not None:
        return error
    visible, error = _mask_raw_html_blocks(visible)
    if error is not None:
        return error
    rendered, error = _mask_markdown_blocks(visible)
    if error is not None:
        return error
    headings = list(_INDEX_HEADING.finditer(rendered))
    if len(headings) != 1:
        return "report must contain exactly one final `## Evidence index` section"

    heading = headings[0]
    body_for_locator_check = rendered[: heading.start()]
    body, error = _mask_inline_code(body_for_locator_check)
    if error is not None:
        return error
    body_ids, error = _parse_marker_ids(body)
    if error is not None:
        return error
    if body_ids is None:
        return "report body contains an invalid citation identifier"
    if not body_ids:
        return "report body must contain at least one numeric inline citation"

    index_ids: dict[int, str] = {}
    index_text = visible[heading.end() :]
    rendered_index_text = rendered[heading.end() :]
    for line, rendered_line in zip(
        index_text.splitlines(),
        rendered_index_text.splitlines(),
    ):
        if not line.strip():
            continue
        if not rendered_line.strip():
            return "Evidence index must not contain Markdown code blocks or hidden rows"
        row = _INDEX_ROW.fullmatch(line)
        if row is None:
            return "Evidence index must be the final section and contain only `- [n] locator` rows"
        raw_id = row.group(1)
        if len(raw_id) > _MAX_CITATION_ID_DIGITS:
            return "Evidence index contains a citation identifier that exceeds the supported size"
        evidence_id = int(raw_id)
        locator = row.group(2).strip()
        if len(locator) >= 2 and locator.startswith("`") and locator.endswith("`"):
            locator = locator[1:-1].strip()
        if not locator:
            return f"Evidence index [{evidence_id}] is missing a source locator"
        if evidence_id in index_ids:
            return f"Evidence index contains duplicate citation id [{evidence_id}]"
        if evidence_id not in locators:
            return f"Evidence index contains citation id absent from evidence_registry: [{evidence_id}]"
        if locator != locators[evidence_id]:
            return f"Evidence index [{evidence_id}] does not match the evidence_registry locator"
        index_ids[evidence_id] = locator

    unknown_body_ids = sorted(body_ids - set(locators))
    if unknown_body_ids:
        return f"report contains citation identifiers absent from evidence_registry: {unknown_body_ids}"
    for evidence_id, locator in locators.items():
        if _body_contains_locator(body_for_locator_check, locator):
            if evidence_id in body_ids:
                return f"report body must use compact citation [{evidence_id}] without repeating its source locator"
            return "report body must not contain an unused evidence source locator"
    if set(index_ids) != body_ids:
        missing_ids = sorted(body_ids - set(index_ids))
        unused_ids = sorted(set(index_ids) - body_ids)
        details = []
        if missing_ids:
            details.append(f"missing body citation ids {missing_ids}")
        if unused_ids:
            details.append(f"unused index citation ids {unused_ids}")
        return "Evidence index must map exactly the ids used in the report body (" + "; ".join(details) + ")"
    return None


def missing_substantive_report_sections(
    report_text: str,
    declared_sections: object,
) -> str | None:
    """Validate declared report sections against rendered Markdown content."""
    if not isinstance(declared_sections, list) or not declared_sections:
        return "report_sections must declare the report's substantive sections"
    if any(not isinstance(section, str) or not section.strip() for section in declared_sections):
        return "report_sections must contain non-empty section names"

    rendered, error = rendered_report_text(report_text)
    if error is not None:
        return error
    if rendered is None:
        return "report could not be rendered"
    index = _INDEX_HEADING.search(rendered)
    body = rendered if index is None else rendered[: index.start()]
    all_headings = [
        (match.start(), match.end(), match.group(2).strip())
        for match in _SECTION_HEADING.finditer(body)
    ]
    headings = [
        (start, end, _normalize_section_name(name))
        for start, end, name in all_headings
        if not _is_non_substantive_section(name)
    ]
    if len(headings) < 2:
        return "report must contain at least two substantive Markdown sections"

    heading_names = [name for _, _, name in headings]
    declared_names = [_normalize_section_name(section) for section in declared_sections]
    if heading_names != declared_names:
        missing_headings = [h for h in heading_names if h not in declared_names]
        extra_headings = [h for h in declared_names if h not in heading_names]
        return (
            "report_sections must match the report's rendered Markdown section headings; "
            f"rendered headings not declared: {missing_headings}; "
            f"declared headings not rendered: {extra_headings}"
        )

    for start, end, name in headings:
        next_starts = [heading_start for heading_start, _, _ in all_headings if heading_start > start]
        next_start = min(next_starts, default=len(body))
        content = body[end:next_start]
        if not any(line.strip() for line in content.splitlines()):
            return f"report section {name!r} must contain substantive content"
    return None


def report_scope_line_error(rendered: str, scope_status: str) -> str | None:
    """Require exactly one literal `Report scope: complete|partial` line in the body."""
    marker = f"Report scope: {scope_status}"
    index = _INDEX_HEADING.search(rendered)
    body = rendered if index is None else rendered[: index.start()]
    matches = [line for line in body.splitlines() if line.strip() == marker]
    if len(matches) != 1:
        return f"report must contain the exact `{marker}` line"
    return None


def _body_contains_locator(body: str, locator: str) -> bool:
    """True when a registry locator appears in the body as a standalone token.

    Uses word-boundary matching so a locator slug inside a longer URL or word
    (e.g. ``source-a`` inside ``https://example.com/source-alpha``) does not
    trigger a false positive, and skips very short locators entirely.
    """
    text = locator.strip()
    if len(text) < _MIN_REPEAT_LOCATOR_LENGTH:
        return False
    return re.search(rf"(?<!\w){re.escape(text)}(?!\w)", body) is not None


def _normalize_section_name(name: str) -> str:
    normalized = name.strip()
    normalized = re.sub(r"^[0-9]+[.)、][ \t]+", "", normalized)
    normalized = re.sub(r"[ \t]*[（(][^）)]*[）)][ \t]*$", "", normalized)
    normalized = re.sub(r"[ \t]+#+[ \t]*$", "", normalized)
    return normalized.strip()


def _is_non_substantive_section(name: str) -> bool:
    return _normalize_section_name(name).casefold() in {
        "review card",
        "review checklist",
        "审查卡",
        "审查清单",
    }


def _normalized_path_text(raw_path: object) -> str | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    if raw_path != raw_path.strip():
        return None
    if (
        len(raw_path.encode("utf-8")) > _MAX_SAFE_REPO_PATH_BYTES
        or "\\" in raw_path
        or any(ord(char) < 32 for char in raw_path)
    ):
        return None
    return raw_path


def _lexical_path_parts(normalized: str) -> tuple[bool, list[str]] | None:
    """Return (is_absolute, parts) after rejecting empty, '.' and '..' segments."""
    if normalized.startswith("/"):
        rest = normalized[1:]
        parts = rest.split("/") if rest else []
        if any(part in ("", ".", "..") for part in parts):
            return None
        return True, parts
    if re.match(r"^[A-Za-z]:/", normalized):
        return None
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    return False, parts


def _walk_without_symlinks(root: Path, parts: list[str]) -> Path | None:
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            return None
    return current


def _resolve_safe_path(
    repo_root: str,
    raw_path: object,
    *,
    expect: str,
) -> Path | None:
    normalized = _normalized_path_text(raw_path)
    if normalized is None:
        return None
    parsed = _lexical_path_parts(normalized)
    if parsed is None:
        return None
    is_absolute, parts = parsed
    try:
        if is_absolute:
            walked = _walk_without_symlinks(Path("/"), parts)
            if walked is None:
                return None
            resolved = Path("/").joinpath(*parts).resolve(strict=False) if parts else Path("/").resolve()
        else:
            repo = Path(repo_root).expanduser().resolve()
            walked = _walk_without_symlinks(repo, parts)
            if walked is None:
                return None
            resolved = repo.joinpath(*parts).resolve(strict=False)
            resolved.relative_to(repo)
        if resolved.is_symlink():
            return None
        if expect == "file" and not resolved.is_file():
            return None
        if expect == "dir" and not resolved.is_dir():
            return None
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def resolve_safe_repo_file(repo_root: str, raw_path: object) -> Path | None:
    return _resolve_safe_path(repo_root, raw_path, expect="file")


def resolve_safe_repo_directory(repo_root: str, raw_path: object) -> Path | None:
    return _resolve_safe_path(repo_root, raw_path, expect="dir")


def report_path_is_within_output_dir(
    repo_root: str,
    raw_report_path: object,
    raw_output_dir: object,
) -> bool:
    """Authorize a report path when the workflow declares an output directory."""
    if raw_output_dir in (None, ""):
        return True
    report = resolve_safe_repo_file(repo_root, raw_report_path)
    output_dir = resolve_safe_repo_directory(repo_root, raw_output_dir)
    if report is None or output_dir is None:
        return False
    try:
        report.relative_to(output_dir)
        return True
    except ValueError:
        return False


def load_utf8_report(repo_root: str, raw_path: object) -> tuple[str | None, str | None]:
    """Return (report_text, None) or (None, error_message) for a readable report file."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "report_path is missing"
    candidate = resolve_safe_repo_file(repo_root, raw_path)
    if candidate is None:
        return None, "report_path must point to a readable regular report file"
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
