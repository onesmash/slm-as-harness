#!/usr/bin/env python3
"""
Context Index — Codex CLI PostToolUse Hook

Reads Codex hook JSON from stdin, delegates to lib_indexer, outputs Codex hook response.

Fails open: any error → exit 0 (pass through original result).
"""

import json
import os
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

from lib_indexer import process_tool_output, write_meta_file, format_index_text

# ── Codex-specific config ─────────────────────────────────────────────────
THRESHOLD_TOKENS = int(os.environ.get("INDEXER_THRESHOLD_TOKENS", "2000"))
RESULTS_DIR      = Path(os.environ.get("INDEXER_RESULTS_DIR",
                         Path.home() / ".codex" / "tool-results"))

SKIP_TOOLS = frozenset({"apply_patch", "Edit", "Write"})

RETRIEVAL_HINT = (
    "Use `sed -n` tool with offset=<line_start> limit=<lines> to fetch specific chunks."
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
        if tool_name in ("Bash", "apply_patch"):
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
    return bool(re.search(r"(?:^|[;&|() \t])sed\s+-n(?:\s|$)", command.lower()))


def emit_pass_through(token_count=None) -> None:
    payload = {"continue": True}
    if token_count is not None:
        payload["token_count_estimate"] = token_count
    print(json.dumps(payload))


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        emit_pass_through()
        return

    tool_name     = event.get("tool_name", "unknown")
    tool_input    = event.get("tool_input", {})
    tool_response = event.get("tool_response", {})
    session_id    = event.get("session_id", "")

    if should_skip(tool_name, tool_input):
        emit_pass_through()
        return

    # Extract text content from Codex hook format
    if isinstance(tool_response, str):
        content = tool_response
    elif isinstance(tool_response, dict):
        content = to_text(tool_response.get("output") or tool_response.get("content") or tool_response)
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
        emit_pass_through(token_count=result["token_count"])

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
        meta_path = write_meta_file(RESULTS_DIR, session_id, raw_file, meta, "_hook_output")
        print(json.dumps({
            "continue": False,
            "stopReason": f"{msg}\nHook output: {meta_path}",
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
