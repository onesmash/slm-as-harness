#!/usr/bin/env python3
"""
Context Index — Cursor postToolUse Hook

Reads Cursor hook JSON from stdin, delegates to lib_indexer, outputs Cursor hook
response.

Cursor (per cursor.com/cn/docs/hooks) gives different replacement powers
depending on the tool category:

  - MCP tools (tool_name starts with "MCP:"): the hook may return
    `updated_mcp_tool_output` to REPLACE the raw tool output the model sees.
    This is a clean substitution, like Codex's `continue:false` or pi's
    extension return value.

  - Shell / Grep / Task etc: only `additional_context` is supported, which
    APPENDS to the model's view. The raw output still flows through this turn;
    savings accrue on follow-up turns when the agent reads chunks from the
    saved file instead of re-running the command.

  - Read / Write / Delete: skipped — outputs are tiny or destructive-side-only.

Fails open: any error (Ollama down, malformed JSON, model missing) → exit 0
with empty stdout → original tool output passes through unchanged.
"""

import json
import os
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

from lib_indexer import process_tool_output, write_meta_file, format_index_text

# ── Cursor-specific config ────────────────────────────────────────────────
THRESHOLD_TOKENS = int(os.environ.get("INDEXER_THRESHOLD_TOKENS", "2000"))
RESULTS_DIR      = Path(os.environ.get("INDEXER_RESULTS_DIR",
                         Path.home() / ".cursor" / "tool-results"))

# Cursor tool types that never produce large text worth indexing, or that we
# never want to perturb (Delete is one-shot side-effects; Read/Write outputs
# are tiny). Task wraps a subagent whose own postToolUse hook already fires
# for each of its tool calls, so re-indexing the rolled-up summary just adds
# noise.
SKIP_TOOLS = frozenset({
    "Read",
    "Write",
    "Delete",
    "Task",
})

RETRIEVAL_HINT = (
    "Use `sed -n '<line_start>,<line_end>p' <file>` to fetch specific chunks from "
    "the saved file. Avoid re-running the original command — it is already saved "
    "at the path above."
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
        if tool_name == "Shell":
            command = tool_input.get("command")
            return command.strip() if isinstance(command, str) else ""
        return json.dumps(tool_input, ensure_ascii=False)
    if isinstance(tool_input, str):
        # MCP gives tool_input as a JSON-encoded string per the spec.
        return tool_input.strip()
    return str(tool_input).strip()


def should_skip(tool_name: str, tool_input) -> bool:
    if tool_name in SKIP_TOOLS:
        return True
    if tool_name != "Shell":
        return False
    # Don't index sed -n chunk reads — that would recursively index our own
    # chunk retrievals and defeat the saved-file design.
    command = ""
    if isinstance(tool_input, dict):
        cmd = tool_input.get("command")
        if isinstance(cmd, str):
            command = cmd.strip()
    if not command:
        return False
    return bool(re.search(r"(?:^|[;&|() \t])sed\s+-n(?:\s|$)", command.lower()))


def emit_pass_through() -> None:
    sys.exit(0)


def extract_tool_output_text(tool_output) -> str:
    """Cursor passes tool_output as a 'string (JSON)' per the spec.

    Some MCP tools embed a structured payload (e.g. {content: [{type:"text",
    text:"..."}]}); others are plain strings. Try to recover human-readable
    text without losing fidelity.
    """
    if tool_output is None:
        return ""
    if isinstance(tool_output, (dict, list)):
        return _flatten_structured(tool_output)
    if not isinstance(tool_output, str):
        return str(tool_output)
    s = tool_output.strip()
    if not s:
        return ""
    if s[:1] in "{[":
        try:
            parsed = json.loads(s)
            return _flatten_structured(parsed)
        except json.JSONDecodeError:
            pass
    return s


def _flatten_structured(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("content", "output", "text", "stdout"):
            if key in value:
                return _flatten_structured(value[key])
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(_flatten_structured(item))
        return "\n".join(p for p in parts if p) or json.dumps(value, ensure_ascii=False)
    return str(value)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        emit_pass_through()
        return

    tool_name       = event.get("tool_name", "unknown")
    tool_input      = event.get("tool_input", {})
    tool_output     = event.get("tool_output", "")
    conversation_id = event.get("conversation_id", "") or event.get("session_id", "")

    if should_skip(tool_name, tool_input):
        emit_pass_through()
        return

    content   = extract_tool_output_text(tool_output)
    input_str = extract_tool_input_for_prompt(tool_name, tool_input)

    result = process_tool_output(
        content=content,
        tool_name=tool_name,
        tool_input=input_str,
        base_dir=RESULTS_DIR,
        session_id=conversation_id,
        threshold_tokens=THRESHOLD_TOKENS,
    )

    if result["action"] == "pass_through":
        emit_pass_through()

    elif result["action"] == "indexed":
        raw_file = Path(result["raw_file"])
        is_mcp = tool_name.startswith("MCP:")
        msg = format_index_text(
            result["index"], str(raw_file), result["token_count"], RETRIEVAL_HINT
        )
        meta = {
            "tool_name": tool_name,
            "conversation_id": conversation_id,
            "raw_result_file": result["raw_file"],
            "token_count_estimate": result["token_count"],
            "threshold_tokens": THRESHOLD_TOKENS,
            "reason": msg,
            "index": result["index"],
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_meta_file(RESULTS_DIR, conversation_id, raw_file, meta, "_hook_output")

        if is_mcp:
            # Full substitution: the model sees ONLY the index, raw output is
            # gone from the turn (savings show up immediately).
            response = {
                "updated_mcp_tool_output": {
                    "content": [{"type": "text", "text": msg}],
                },
            }
        else:
            # Cursor's postToolUse for non-MCP tools cannot strip the raw
            # output — only append context. Savings accrue on follow-up turns
            # when the agent reads from the saved file.
            response = {"additional_context": msg}

        print(json.dumps(response))

    else:  # error
        error_info = {
            "tool_name": tool_name,
            "conversation_id": conversation_id,
            "raw_result_file": result.get("raw_file", ""),
            "token_count_estimate": result["token_count"],
            "error_type": result.get("error_type", ""),
            "error_message": result.get("error", ""),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_meta_file(
            RESULTS_DIR, conversation_id,
            Path(result.get("raw_file", "unknown")),
            error_info, "_hook_error",
        )
        emit_pass_through()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        emit_pass_through()
