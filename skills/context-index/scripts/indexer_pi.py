#!/usr/bin/env python3
"""
Context Index — pi Extension Backend

stdin:  {content, tool_name, tool_input, output_dir, session_id}
stdout: {action, ...} from lib_indexer.process_tool_output
"""

import json, os, sys
from pathlib import Path
from lib_indexer import process_tool_output, format_index_text, write_meta_file

THRESHOLD_TOKENS = int(os.environ.get("INDEXER_THRESHOLD_TOKENS", "2000"))
DEFAULT_OUTPUT   = Path(os.environ.get("INDEXER_RESULTS_DIR",
                         Path.home() / ".pi" / "tool-results"))
RETRIEVAL_HINT   = (
    "Use `read` with offset=<line_start> limit=<lines> to fetch specific chunks."
)

def main():
    try:
        req = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"action": "error", "error": "Invalid input JSON"}))
        return

    tool_input = req.get("tool_input", "")
    if isinstance(tool_input, dict):
        tool_input = json.dumps(tool_input)

    output_dir = Path(req.get("output_dir", str(DEFAULT_OUTPUT)))
    session_id = req.get("session_id", "pi-session")

    result = process_tool_output(
        content=req.get("content", ""),
        tool_name=req.get("tool_name", "unknown"),
        tool_input=tool_input,
        base_dir=output_dir,
        session_id=session_id,
        threshold_tokens=THRESHOLD_TOKENS,
    )

    if result["action"] == "indexed":
        result["formatted"] = format_index_text(
            result["index"], result["raw_file"], result["token_count"], RETRIEVAL_HINT
        )
        write_meta_file(
            base_dir=output_dir,
            session_id=session_id,
            result_file=Path(result["raw_file"]),
            payload=result,
            suffix="_hook_output",
        )
    elif result["action"] == "error":
        write_meta_file(
            base_dir=output_dir,
            session_id=session_id,
            result_file=Path(result.get("raw_file", "unknown")),
            payload=result,
            suffix="_hook_error",
        )

    print(json.dumps(result))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({"action": "error", "error": "Unhandled exception"}))
