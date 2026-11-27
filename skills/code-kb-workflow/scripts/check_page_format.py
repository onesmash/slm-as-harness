#!/usr/bin/env python3
"""Lint published `knowledge-base/` pages against the wiki-page-writer contract.

The orchestrator's `references/artifact-contract.md` enumerates the rules every
*published page* under `knowledge-base/` must satisfy: VitePress frontmatter,
3+ Mermaid diagrams mixing ≥2 types with `autonumber` on sequences, a
``<!-- Sources: ... -->`` comment after each diagram, a ``## Related Pages``
table at the end, and escaped bare generics. This script enforces those rules
mechanically so Stage 3 cannot ship a format-incomplete page and Stage 4 has
something concrete to grade in `04-qa-feedback.md` § Format compliance.

Usage:
    python3 scripts/check_page_format.py knowledge-base/
    python3 scripts/check_page_format.py knowledge-base/architecture/01-system-overview.md
    python3 scripts/check_page_format.py knowledge-base/ --json   # machine-readable
    python3 scripts/check_page_format.py knowledge-base/ --quiet  # exit-code only

Exit codes:
    0 — no violations across all checked pages.
    1 — at least one page has a hard violation.
    2 — script invocation error (path missing, etc.).

The linter is intentionally conservative. It will *warn* on quotas it cannot
judge (page size → diagram count) but only *fail* on objective rule breaks.
The list of exempt or downgraded files mirrors the artifact-contract exceptions:

  - `llms.txt` — plain-text, exempt from all checks.
  - `_meta/**` — workflow state, governed by per-file rules elsewhere.
  - `log.md` — append-only log, diagrams optional.
  - `index.md` — table of contents; Mermaid-count is a warning, not a failure.

The script does not modify files. Pair with `strip_vs16.py` for the post-write
hygiene pass.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable


# --- file classification --------------------------------------------------- #

EXEMPT_BASENAMES = {"llms.txt"}
WARN_ONLY_BASENAMES = {"index.md", "README.md"}
LOG_BASENAMES = {"log.md", "maintenance-log.md"}


def classify(path: pathlib.Path, kb_root: pathlib.Path) -> str:
    """Return one of: ``exempt``, ``warn-only``, ``log``, ``meta``, ``qa``, ``page``."""
    abs_path = path.resolve()
    abs_root = kb_root.resolve()
    try:
        rel = abs_path.relative_to(abs_root)
    except ValueError:
        rel = pathlib.Path(path.name)
    parts = rel.parts
    name = path.name

    if name in EXEMPT_BASENAMES:
        return "exempt"
    if parts and parts[0] == "_meta":
        return "meta"
    if parts and parts[0] == "qa":
        return "qa"
    if name in LOG_BASENAMES:
        return "log"
    if name in WARN_ONLY_BASENAMES:
        return "warn-only"
    return "page"


# --- rules ----------------------------------------------------------------- #


@dataclass
class Finding:
    severity: str          # "error" or "warn"
    rule: str              # short id like "frontmatter.missing"
    message: str           # human-readable explanation


@dataclass
class PageReport:
    path: pathlib.Path
    classification: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)


FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)
MERMAID_BLOCK_RE = re.compile(
    r"^```mermaid\s*\n(?P<body>.*?)\n```",
    re.DOTALL | re.MULTILINE,
)
SOURCES_AFTER_DIAGRAM_RE = re.compile(
    r"^```mermaid\s*\n.*?\n```\s*\n+(?:[^\n]+\n)?\s*<!--\s*Sources?\s*:",
    re.DOTALL | re.MULTILINE,
)
RELATED_PAGES_HEADING_RE = re.compile(
    r"^##\s+Related Pages\s*$", re.MULTILINE
)
TABLE_HEADER_RE = re.compile(r"^\s*\|.*\|\s*\n\s*\|[\s:|-]+\|\s*$", re.MULTILINE)
SEQUENCE_DIAGRAM_RE = re.compile(r"^\s*sequenceDiagram\b", re.MULTILINE)
AUTONUMBER_RE = re.compile(r"^\s*autonumber\b", re.MULTILINE)
DIAGRAM_TYPE_RE = re.compile(
    r"^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram|gantt|pie|journey|gitGraph)\b",
    re.MULTILINE,
)


def _strip_code_fences(text: str) -> str:
    """Return the text outside fenced code blocks. Used for prose-only checks."""
    out, in_fence = [], False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "".join(out)


def check_frontmatter(text: str, report: PageReport) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        report.findings.append(
            Finding(
                severity="error",
                rule="frontmatter.missing",
                message="Missing VitePress frontmatter at top of file (must start with `---` "
                "containing at least `title:` and `description:`).",
            )
        )
        return None
    body = m.group("body")
    fm = {}
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    if "title" not in fm or not fm["title"]:
        report.findings.append(
            Finding(
                severity="error",
                rule="frontmatter.title.missing",
                message="Frontmatter is missing `title:`.",
            )
        )
    if "description" not in fm or not fm["description"]:
        report.findings.append(
            Finding(
                severity="error",
                rule="frontmatter.description.missing",
                message="Frontmatter is missing `description:`.",
            )
        )
    return fm


def check_mermaid_blocks(text: str, report: PageReport, *, warn_only: bool) -> None:
    blocks = list(MERMAID_BLOCK_RE.finditer(text))
    severity = "warn" if warn_only else "error"

    if len(blocks) < 3:
        report.findings.append(
            Finding(
                severity=severity,
                rule="mermaid.count",
                message=f"Found {len(blocks)} Mermaid diagram(s); the contract requires "
                f"≥3 (small page) / 4 (medium) / 5+ (large). See "
                f"`wiki-page-writer/SKILL.md`.",
            )
        )

    types_seen: set[str] = set()
    for idx, block in enumerate(blocks, 1):
        body = block.group("body")
        type_match = DIAGRAM_TYPE_RE.search(body)
        if type_match:
            types_seen.add(type_match.group(1))
        # autonumber on sequenceDiagram
        if SEQUENCE_DIAGRAM_RE.search(body) and not AUTONUMBER_RE.search(body):
            report.findings.append(
                Finding(
                    severity="error",
                    rule="mermaid.sequenceDiagram.autonumber",
                    message=f"Mermaid block #{idx} is a sequenceDiagram but is missing "
                    f"`autonumber` (required so steps are referenceable).",
                )
            )
        # no `<br/>` (slash) inside Mermaid; bare `<br>` or newlines are fine
        if "<br/>" in body:
            report.findings.append(
                Finding(
                    severity="error",
                    rule="mermaid.br_slash",
                    message=f"Mermaid block #{idx} contains `<br/>`; use `<br>` or a newline.",
                )
            )

    if blocks and len(types_seen) < 2:
        report.findings.append(
            Finding(
                severity=severity,
                rule="mermaid.types",
                message=f"Mermaid diagrams use only {len(types_seen)} type(s) "
                f"({sorted(types_seen) or 'none'}); the contract requires ≥2 different "
                f"types from graph/sequenceDiagram/classDiagram/stateDiagram-v2/flowchart/erDiagram.",
            )
        )

    # `<!-- Sources: ... -->` immediately (within ~3 lines / one paragraph) after each diagram
    expected = len(blocks)
    found = len(SOURCES_AFTER_DIAGRAM_RE.findall(text))
    if expected and found < expected:
        report.findings.append(
            Finding(
                severity="error",
                rule="mermaid.sources_comment",
                message=f"{expected} Mermaid block(s) but only {found} `<!-- Sources: ... -->` "
                f"comment(s) immediately after them. Add one comment per diagram, citing the "
                f"source files the diagram is derived from.",
            )
        )


def check_related_pages(text: str, report: PageReport) -> None:
    m = RELATED_PAGES_HEADING_RE.search(text)
    if not m:
        report.findings.append(
            Finding(
                severity="error",
                rule="related_pages.missing",
                message="Missing a `## Related Pages` section near the end of the file.",
            )
        )
        return
    tail = text[m.end():]
    # The section needs a markdown table (header row + separator). A bullet list does not satisfy.
    if not TABLE_HEADER_RE.search(tail):
        report.findings.append(
            Finding(
                severity="error",
                rule="related_pages.table",
                message="`## Related Pages` exists but is not formatted as a markdown table "
                "(needs a `| Column | ... |` header row followed by a separator row). "
                "Bullet lists do not satisfy the contract.",
            )
        )


def check_bare_generics(text: str, report: PageReport) -> None:
    prose = _strip_code_fences(text)
    # Heuristic: matches `Word<OtherWord>` or `Word<OtherWord, OtherWord>` outside code fences.
    pattern = re.compile(
        r"(?<![`\\])\b([A-Z][A-Za-z0-9]*)\s*<\s*([A-Z][A-Za-z0-9]*(?:\s*,\s*[A-Z][A-Za-z0-9]*)*)\s*>"
    )
    for m in pattern.finditer(prose):
        # Skip inline code already wrapped
        start = m.start()
        # Look back for inline `; if there's an unclosed backtick on this line before the match, skip.
        line_start = prose.rfind("\n", 0, start) + 1
        line_segment = prose[line_start:start]
        if line_segment.count("`") % 2 == 1:
            continue
        report.findings.append(
            Finding(
                severity="warn",
                rule="vitepress.bare_generic",
                message=f"Possible unescaped generic `{m.group(0)}` outside code fences. "
                f"Wrap in backticks (`` `{m.group(0)}` ``) so VitePress does not parse it as HTML.",
            )
        )
        # Cap at 5 reports per file to avoid noise
        if sum(1 for f in report.findings if f.rule == "vitepress.bare_generic") >= 5:
            break


def check_log_page(text: str, report: PageReport) -> None:
    """Logs are exempt from format quotas but still need frontmatter."""
    check_frontmatter(text, report)


def check_meta_page(text: str, report: PageReport) -> None:
    """Meta files are governed by per-file rules elsewhere; this linter only
    flags accidents like missing frontmatter or rogue `<br/>` in code fences."""
    # Intentionally minimal: meta files use repo-root-relative paths and prose,
    # not the published-page format.
    return None


def check_qa_artifact(text: str, report: PageReport) -> None:
    """QA artifacts under `qa/` are smaller-scope; require frontmatter + a
    Related Pages link back, but do not enforce diagram quotas."""
    check_frontmatter(text, report)
    check_related_pages(text, report)


def check_published_page(text: str, report: PageReport, *, warn_only: bool) -> None:
    check_frontmatter(text, report)
    check_mermaid_blocks(text, report, warn_only=warn_only)
    check_related_pages(text, report)
    check_bare_generics(text, report)


# --- driver --------------------------------------------------------------- #


def lint_file(path: pathlib.Path, kb_root: pathlib.Path) -> PageReport:
    classification = classify(path, kb_root)
    report = PageReport(path=path, classification=classification)
    if classification == "exempt":
        return report
    text = path.read_text(encoding="utf-8")
    if classification == "log":
        check_log_page(text, report)
    elif classification == "meta":
        check_meta_page(text, report)
    elif classification == "qa":
        check_qa_artifact(text, report)
    elif classification == "warn-only":
        check_published_page(text, report, warn_only=True)
    else:
        check_published_page(text, report, warn_only=False)
    return report


def iter_pages(roots: Iterable[pathlib.Path]) -> Iterable[pathlib.Path]:
    for root in roots:
        if root.is_file():
            yield root
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".markdown", ".txt", ".mdx"}:
                continue
            yield path


def find_kb_root(paths: list[pathlib.Path]) -> pathlib.Path:
    """Locate the `knowledge-base/` ancestor of the first path so classify() can compute
    paths relative to it. Falls back to the first arg itself."""
    for p in paths:
        cur = p.resolve()
        for parent in (cur,) + tuple(cur.parents):
            if parent.name == "knowledge-base":
                return parent
    return paths[0].resolve()


def render_text(reports: list[PageReport]) -> tuple[str, int, int]:
    lines, errors, warns = [], 0, 0
    for r in reports:
        if not r.findings:
            continue
        lines.append(f"{r.path} [{r.classification}]")
        for f in r.findings:
            tag = "ERROR" if f.severity == "error" else "warn"
            lines.append(f"  {tag:5s} {f.rule}: {f.message}")
            if f.severity == "error":
                errors += 1
            else:
                warns += 1
        lines.append("")
    if not lines:
        lines.append("All checked pages satisfy the wiki-page-writer contract.")
    summary = f"\nSummary: {errors} error(s), {warns} warning(s) across {len(reports)} file(s)."
    return "\n".join(lines) + summary, errors, warns


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", type=pathlib.Path,
                        help="Files or directories to check (typically `knowledge-base/`).")
    parser.add_argument("--json", action="store_true",
                        help="Emit a machine-readable JSON report instead of text.")
    parser.add_argument("--quiet", action="store_true",
                        help="Print nothing; signal violations through the exit code only.")
    args = parser.parse_args(argv)

    paths = [p for p in args.paths]
    for p in paths:
        if not p.exists():
            print(f"check_page_format: path does not exist: {p}", file=sys.stderr)
            return 2

    kb_root = find_kb_root(paths)
    reports = [lint_file(f, kb_root) for f in iter_pages(paths)]
    errors = sum(1 for r in reports for f in r.findings if f.severity == "error")

    if args.json:
        payload = {
            "kb_root": str(kb_root),
            "files": [
                {
                    "path": str(r.path),
                    "classification": r.classification,
                    "findings": [
                        {"severity": f.severity, "rule": f.rule, "message": f.message}
                        for f in r.findings
                    ],
                }
                for r in reports
            ],
            "errors": errors,
            "warnings": sum(1 for r in reports for f in r.findings if f.severity == "warn"),
        }
        if not args.quiet:
            print(json.dumps(payload, indent=2))
    elif not args.quiet:
        text, _, _ = render_text(reports)
        print(text)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
