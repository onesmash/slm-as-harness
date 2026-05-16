#!/usr/bin/env python3
"""
Context Index — Claude Code PostToolUse Hook

Reads Claude Code hook JSON from stdin, delegates to lib_indexer, outputs Claude
Code hook response.

Output strategy (per Claude Code hooks reference at code.claude.com/docs/en/hooks):
- Below threshold or skip: exit 0, empty stdout → original tool result passes through.
- Indexed: emit JSON with hookSpecificOutput.updatedToolOutput. The replacement payload
  is the index summary + saved-file path + retrieval hint; the raw tool_response is
  dropped from this turn's context. Follow-up turns retrieve chunks from the saved
  file via `Read` with offset/limit.

Fails open: any error → exit 0 with empty stdout (original result passes through).
"""

import json
import os
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

from lib_indexer import process_tool_output, write_meta_file, format_index_text

# ── Claude Code-specific config ───────────────────────────────────────────
THRESHOLD_TOKENS = int(os.environ.get("INDEXER_THRESHOLD_TOKENS", "2000"))
RESULTS_DIR      = Path(os.environ.get("INDEXER_RESULTS_DIR",
                         Path.home() / ".claude" / "tool-results"))

# Tools whose output is never large enough to warrant indexing, or whose output
# is already line-addressable by Claude Code (Read returns cat -n format).
SKIP_TOOLS = frozenset({
    "Edit",
    "Write",
    "Read",
    "NotebookEdit",
    "TodoWrite",
    "ExitPlanMode",
})

RETRIEVAL_HINT = (
    "Default: trust the summary above. Fetch chunks only when you need a specific "
    "symbol, field, value, or line that you can name in one phrase. "
    "Then use `Read` with offset=<line_start> limit=<line_end - line_start + 1> on "
    "the saved file, picking the MINIMUM chunks that answer your question — not "
    "every chunk that looks relevant. "
    "Reading the saved file with no offset/limit (i.e. the whole file) defeats the "
    "purpose of the index and wastes the tokens that were just saved. If you find "
    "yourself wanting more than ~50% of the chunks, the summary was insufficient: "
    "re-query the original tool with a narrower scope instead of bulk-reading. "
    "The result is already saved at the path above; do not re-run the original command."
)


# ── Helpers ────────────────────────────────────────────────────────────────

def to_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def extract_tool_input_for_prompt(tool_name: str, tool_input) -> str:
    if isinstance(tool_input, dict):
        if tool_name == "Bash":
            command = tool_input.get("command")
            return command.strip() if isinstance(command, str) else ""
        return json.dumps(tool_input, ensure_ascii=False)
    return str(tool_input).strip()


def should_skip(tool_name: str, tool_input) -> bool:
    if tool_name in SKIP_TOOLS:
        return True
    if tool_name != "Bash":
        return False
    command = ""
    if isinstance(tool_input, dict):
        cmd = tool_input.get("command")
        if isinstance(cmd, str):
            command = cmd.strip()
    if not command:
        return False
    # Don't index sed -n chunk reads (avoid recursive indexing of our own chunk fetches)
    return bool(re.search(r"(?:^|[;&|() \t])sed\s+-n(?:\s|$)", command.lower()))


def emit_pass_through() -> None:
    """Exit silently — Claude Code interprets empty stdout + exit 0 as no-op."""
    sys.exit(0)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        emit_pass_through()
        return

    tool_name     = event.get("tool_name", "unknown")
    tool_input    = event.get("tool_input", {})
    tool_response = event.get("tool_response", "")
    session_id    = event.get("session_id", "")

    if should_skip(tool_name, tool_input):
        emit_pass_through()
        return

    # Claude Code tool_response shapes seen in the wild:
    #   - string (Bash stdout/stderr concatenated)
    #   - dict with "content" (list of {type: "text", text}) or "output" or "stdout"
    #   - list of content blocks
    if isinstance(tool_response, str):
        content = tool_response
    elif isinstance(tool_response, dict):
        nested = (
            tool_response.get("content")
            or tool_response.get("output")
            or tool_response.get("stdout")
            or tool_response
        )
        if isinstance(nested, list):
            parts = []
            for item in nested:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    parts.append(item)
            content = "\n".join(parts) if parts else to_text(tool_response)
        else:
            content = to_text(nested)
    elif isinstance(tool_response, list):
        parts = []
        for item in tool_response:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        content = "\n".join(parts) if parts else to_text(tool_response)
    else:
        content = to_text(tool_response)

    input_str = extract_tool_input_for_prompt(tool_name, tool_input)

    result = process_tool_output(
        content=content,
        tool_name=tool_name,
        tool_input=input_str,
        base_dir=RESULTS_DIR,
        session_id=session_id,
        threshold_tokens=THRESHOLD_TOKENS,
    )

    if result["action"] == "pass_through":
        emit_pass_through()

    elif result["action"] == "indexed":
        raw_file = Path(result["raw_file"])
        msg = format_index_text(
            result["index"], str(raw_file), result["token_count"], RETRIEVAL_HINT
        )
        meta = {
            "tool_name": tool_name,
            "session_id": session_id,
            "raw_result_file": result["raw_file"],
            "token_count_estimate": result["token_count"],
            "threshold_tokens": THRESHOLD_TOKENS,
            "reason": msg,
            "index": result["index"],
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_meta_file(RESULTS_DIR, session_id, raw_file, meta, "_hook_output")
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "updatedToolOutput": msg,
            },
        }))

    else:  # error
        error_info = {
            "tool_name": tool_name,
            "session_id": session_id,
            "raw_result_file": result.get("raw_file", ""),
            "token_count_estimate": result["token_count"],
            "error_type": result.get("error_type", ""),
            "error_message": result.get("error", ""),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_meta_file(
            RESULTS_DIR, session_id,
            Path(result.get("raw_file", "unknown")),
            error_info, "_hook_error",
        )
        emit_pass_through()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        emit_pass_through()
