#!/usr/bin/env python3
"""Strip U+FE0F (Variation Selector-16) from generated knowledge-base files.

The variation selector is a zero-width Unicode codepoint that follows
dual-presentation characters (e.g. U+26A0 WARNING SIGN, U+2705 HEAVY
WHITE CHECK MARK) to force them to render as colored emoji rather than
monochrome text. Models trained on web-rendered content tend to emit
the FE0F-decorated form because the public web overwhelmingly uses it.

In a knowledge-base context this is undesirable: FE0F is invisible but
inflates byte counts, breaks naive char-based diffs, makes documents
look noisy in hex-aware tools, and adds platform-dependent rendering.
We prefer the bare codepoint and let the renderer pick its own
presentation.

Usage:
    python -m scripts.strip_vs16 knowledge-base/
    python -m scripts.strip_vs16 path/to/file.md another.md

By default, only files with extensions in EXTS are touched. Pass
``--all-extensions`` to process every file under the given paths.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

VS16 = "️"
EXTS = {".md", ".markdown", ".txt", ".mdx"}


def iter_files(roots: list[pathlib.Path], all_extensions: bool):
    for root in roots:
        if not root.exists():
            print(f"warning: path does not exist: {root}", file=sys.stderr)
            continue
        if root.is_file():
            yield root
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if all_extensions or p.suffix.lower() in EXTS:
                yield p


def strip_file(path: pathlib.Path, dry_run: bool) -> int:
    """Return the number of FE0F codepoints removed from ``path``."""
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return 0
    count = original.count(VS16)
    if count == 0:
        return 0
    if not dry_run:
        path.write_text(original.replace(VS16, ""), encoding="utf-8")
    return count


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        type=pathlib.Path,
        help="Files or directories to clean.",
    )
    parser.add_argument(
        "--all-extensions",
        action="store_true",
        help="Process every file, not just the default text extensions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be stripped without modifying files.",
    )
    args = parser.parse_args(argv)

    total_files = 0
    total_codepoints = 0
    for path in iter_files(args.paths, args.all_extensions):
        removed = strip_file(path, dry_run=args.dry_run)
        if removed:
            total_files += 1
            total_codepoints += removed
            verb = "would strip" if args.dry_run else "stripped"
            print(f"{verb} {removed} U+FE0F from {path}")

    if total_files == 0:
        print("no U+FE0F characters found")
    else:
        verb = "Would remove" if args.dry_run else "Removed"
        print(
            f"{verb} {total_codepoints} U+FE0F codepoint(s) "
            f"across {total_files} file(s)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
