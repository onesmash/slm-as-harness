#!/usr/bin/env python3
"""
Context Index — Shared Library

Pure indexing logic: token estimation, Ollama chat, semantic chunk index building,
and raw-result file saving. Zero platform-specific code.
"""

import json
import os
import re
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Config from environment ────────────────────────────────────────────────
INDEXER_MODEL         = os.environ.get("INDEXER_MODEL", "qwen3.5:4b")
OLLAMA_URL            = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_TIMEOUT_SEC    = float(os.environ.get("INDEXER_OLLAMA_TIMEOUT_SEC", "120"))
CHARS_PER_TOKEN       = 3

# ── System prompt for the small indexer model ─────────────────────────────

SYSTEM_PROMPT = """\
You are a document indexer. Given raw tool output, split into semantic chunks and output structured JSON.

Output format:
{
  "summary": "<overall 1-2 sentence summary>",
  "chunks": [
    { "id": 1, "topic": "<3-5 words>", "summary": "<what this chunk contains>", "line_start": 1, "line_end": 23 },
    ...
  ]
}

Rules:
- Chunk boundaries = semantic units (one command section, one result entry, one object)
- topic = 3-5 words max
- summary = what the chunk contains, not a paraphrase
- line numbers = exact, 1-indexed, covering the entire document with no gaps and no overlaps
- Output valid JSON only, no commentary outside the JSON"""


# ── Public API ─────────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Rough token count for threshold gating."""
    return len(text) // CHARS_PER_TOKEN


def call_ollama(
    system_prompt: str,
    user_prompt: str,
    model: str = INDEXER_MODEL,
    url: str = OLLAMA_URL,
    timeout: float = OLLAMA_TIMEOUT_SEC,
) -> str:
    """Call Ollama chat API and return the model's text response."""
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "think": False,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{url}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["message"]["content"]


def build_index(
    tool_name: str,
    tool_input: str,
    content: str,
    model: str = INDEXER_MODEL,
    url: str = OLLAMA_URL,
    timeout: float = OLLAMA_TIMEOUT_SEC,
) -> dict:
    """
    Call the small model to produce a semantic chunk index.

    Returns: { "summary": str, "chunks": [ {id, topic, summary, line_start, line_end}, ... ] }
    """
    user_msg = f"Tool: {tool_name}\nCommand: {tool_input}\n\n{content}"
    raw = call_ollama(SYSTEM_PROMPT, user_msg, model=model, url=url, timeout=timeout)

    # Strip markdown code fences if the model wrapped its JSON output
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    return json.loads(raw)


def write_result_file(
    base_dir: Path,
    session_id: str,
    tool_name: str,
    content: str,
) -> Path:
    """Save raw tool output to disk. Returns the file path."""
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    # Strip filesystem-hostile chars (`:` from Cursor's `MCP:tool` names breaks Windows paths).
    safe_tool = re.sub(r"[^A-Za-z0-9._-]", "_", tool_name)[:40]
    subdir = base_dir / (session_id or "unknown")
    subdir.mkdir(parents=True, exist_ok=True)
    path = subdir / f"{safe_tool}_{ts}_{content_hash}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def write_meta_file(
    base_dir: Path,
    session_id: str,
    result_file: Path,
    payload: dict,
    suffix: str = "_meta",
) -> Path:
    """Write a JSON metadata file next to the result file. Returns the path."""
    subdir = base_dir / (session_id or "unknown")
    subdir.mkdir(parents=True, exist_ok=True)
    path = subdir / f"{result_file.stem}{suffix}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def format_index_text(
    index: dict,
    raw_file: str,
    token_count: int,
    retrieval_hint: str = "",
) -> str:
    """
    Format a semantic chunk index into a human-readable text block for the agent.

    retrieval_hint: platform-specific instruction for chunk retrieval
        (e.g. 'Use `sed -n` ...' for Codex, 'Use `read` with offset=...' for pi).
    """
    chunks_txt = "\n".join(
        f'  [{c["id"]}] lines {c["line_start"]}-{c["line_end"]} | {c["topic"]} — {c["summary"]}'
        for c in index.get("chunks", [])
    )
    parts = [
        f"Output too large (~{token_count} tokens). Saved and indexed.",
        "",
        f"Summary: {index.get('summary', '')}",
        f"File: {raw_file}",
        "",
        "Chunks:",
        chunks_txt,
    ]
    if retrieval_hint:
        parts.extend(["", retrieval_hint])
    return "\n".join(parts)


def process_tool_output(
    content: str,
    tool_name: str,
    tool_input: str,
    base_dir: Path,
    session_id: str,
    threshold_tokens: int,
) -> dict:
    """
    Full indexing flow: threshold check, save to disk, semantic index.

    Platform-agnostic. Each wrapper formats the result dict for its own I/O.

    Returns one of:
      {"action": "pass_through", "token_count": N}
      {"action": "indexed",    "index": {...}, "raw_file": str, "token_count": N}
      {"action": "error",      "error": str, "error_type": str, "raw_file": str, "token_count": N}
    """
    token_count = estimate_tokens(content)
    if token_count < threshold_tokens:
        return {"action": "pass_through", "token_count": token_count}

    file_path = write_result_file(base_dir, session_id, tool_name, content)

    try:
        index = build_index(tool_name, tool_input, content)
        return {
            "action": "indexed",
            "index": index,
            "raw_file": str(file_path),
            "token_count": token_count,
        }
    except Exception as e:
        return {
            "action": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "raw_file": str(file_path),
            "token_count": token_count,
        }
