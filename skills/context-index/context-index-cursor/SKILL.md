---
name: context-index-cursor
description: >
  Install the Context Index hook for Cursor — a postToolUse hook that saves
  large tool outputs to disk, indexes them with a local small model (qwen3.5:4b
  via Ollama), and either fully replaces the model's view of the output (for
  MCP tools, via `updated_mcp_tool_output`) or appends a chunk index as
  `additional_context` (for Shell/Grep/Task). On follow-up turns the agent
  fetches specific chunks from the saved file instead of re-running the
  command.

  Use this skill when the user is on Cursor (the AI editor from cursor.com)
  and wants to install the context-index hook, or when the main context-index
  skill routes to this sub-skill for Cursor setup.
---

# Context Index Hook — Cursor

> This is a sub-skill of `context-index`. It installs the `postToolUse` hook
> for [Cursor](https://cursor.com), following the
> [Cursor hooks reference](https://cursor.com/cn/docs/hooks).

## Prerequisite: shared engine

The Python scripts live in the parent skill's `scripts/` directory. Both
`lib_indexer.py` (shared library) and `indexer_cursor.py` (Cursor wrapper) must
be copied together:

```bash
PARENT_SKILL_DIR="<path-to-skills>/context-index"
ls "$PARENT_SKILL_DIR/scripts/lib_indexer.py"     # shared library
ls "$PARENT_SKILL_DIR/scripts/indexer_cursor.py"  # Cursor wrapper
```

## What this installs

A `postToolUse` hook in `~/.cursor/hooks.json` (or `<project>/.cursor/hooks.json`)
that:

1. Fires after every tool call. Internally we skip `Read`, `Write`, `Delete`,
   `Task`, and `sed -n` chunk reads — none of those benefit from indexing.
2. If `tool_output` exceeds the token threshold (default: 2000 tokens ≈ 6000
   chars), saves the raw output to `~/.cursor/tool-results/<conversation_id>/`.
3. Calls a local `qwen3.5:4b` model via Ollama for a semantic chunk index.
4. Branches on tool category:
   - **MCP tools** (`tool_name` starts with `MCP:`): returns
     `updated_mcp_tool_output` containing the index. The raw output is
     **replaced** — the model only sees the compact index. Real first-turn
     token savings.
   - **Shell / Grep**: returns `additional_context` with the index. Cursor's
     `postToolUse` cannot strip the raw output for non-MCP tools; the index
     is **appended**. First-turn cost is unchanged; savings accrue on
     follow-up turns via chunked reads from the saved file.

**Fails open**: any error (Ollama down, model missing, timeout, malformed JSON)
→ wrapper exits 0 with empty stdout → original tool output passes through.

### Substitution semantics in one table

| Tool category | Mechanism                       | First-turn raw output |
|---------------|---------------------------------|-----------------------|
| `MCP:*`       | `updated_mcp_tool_output`       | **Replaced** by index |
| `Shell`, `Grep` | `additional_context`          | Still shown; index appended |
| `Read`, `Write`, `Delete`, `Task` | Skipped       | Untouched             |

This split is forced by Cursor's hook contract, not a design choice — the docs
explicitly limit `updated_mcp_tool_output` to MCP tools.

---

## Step 1 — Check prerequisites

```bash
# Cursor (open Cursor → Help → About to read the version)
# Python 3.8+
python3 --version
```

---

## Step 2 — Install Ollama

```bash
ollama --version || brew install ollama   # macOS/Linux
# or: curl -fsSL https://ollama.com/install.sh | sh

ollama serve &
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```

---

## Step 3 — Pull the indexer model

```bash
ollama pull qwen3.5:4b
ollama list | grep qwen3.5
```

---

## Step 4 — Install the hook scripts

```bash
mkdir -p ~/.cursor/hooks
cp <PARENT_SKILL_DIR>/scripts/lib_indexer.py     ~/.cursor/hooks/lib_indexer.py
cp <PARENT_SKILL_DIR>/scripts/indexer_cursor.py  ~/.cursor/hooks/indexer_cursor.py
chmod +x ~/.cursor/hooks/indexer_cursor.py
```

Smoke-test the wrapper directly (Ollama must be running):

```bash
echo '{
  "tool_name": "Shell",
  "tool_input": {"command": "ls /usr/lib"},
  "tool_output": "'"$(printf 'libfoo.dylib\n%.0s' {1..2000})"'",
  "conversation_id": "smoke-test"
}' | python3 ~/.cursor/hooks/indexer_cursor.py
```

Expected: a JSON blob with `additional_context` containing the index. Empty
stdout means pass-through (below threshold, skipped tool, or fail-open).

For the MCP path, swap `"tool_name": "Shell"` for `"tool_name": "MCP:my_tool"`
and you should see `{"updated_mcp_tool_output": {"content": [...]}}` instead.

---

## Step 5 — Register the hook in `~/.cursor/hooks.json`

**If the file does NOT exist**, create it:

```bash
cat > ~/.cursor/hooks.json << 'EOF'
{
  "version": 1,
  "hooks": {
    "postToolUse": [
      {
        "command": "python3 ~/.cursor/hooks/indexer_cursor.py",
        "type": "command",
        "timeout": 120
      }
    ]
  }
}
EOF
```

**If the file already exists**, merge the `postToolUse` block with `jq`:

```bash
TMP=$(mktemp)
jq '.version = (.version // 1)
  | .hooks.postToolUse = ((.hooks.postToolUse // []) + [{
      "command": "python3 ~/.cursor/hooks/indexer_cursor.py",
      "type": "command",
      "timeout": 120
    }])' ~/.cursor/hooks.json > "$TMP" && mv "$TMP" ~/.cursor/hooks.json
```

Notes:

- No `matcher` is set — the wrapper's internal `SKIP_TOOLS` filter handles
  exclusions. If you'd rather skip at the matcher level (one fewer Python
  spawn per Read/Write call), use a separate hook entry per tool:

  ```json
  { "command": "...", "type": "command", "timeout": 120, "matcher": "Shell" },
  { "command": "...", "type": "command", "timeout": 120, "matcher": "Grep"  },
  { "command": "...", "type": "command", "timeout": 120, "matcher": "MCP:.*" }
  ```

- We **do not** set `failClosed: true`. If Ollama is down or the wrapper
  crashes, the operation must still succeed — the agent just sees the raw
  output (default `failClosed: false`). For an indexing/observation hook,
  fail-open is the right default; `failClosed` is for security gates.

Verify:

```bash
jq '.hooks.postToolUse' ~/.cursor/hooks.json
```

---

## Step 6 — Reload Cursor

Restart Cursor (or reload the window: `Cmd+Shift+P` → "Developer: Reload
Window"). Hooks load on session start.

---

## Step 7 — Smoke test inside Cursor

Open an Agent/Composer session and run a command with large output, e.g.:

> Run `find /usr/lib -name '*.dylib' 2>/dev/null | head -200` and tell me what
> kinds of libraries are there.

Expected:

- The hook fires after the `Shell` call.
- A file appears under
  `~/.cursor/tool-results/<conversation_id>/Shell_<ts>_<hash>.txt`.
- The agent sees the raw output AND an injected `additional_context` block
  with the chunk index pointing at the saved file.
- Follow-up questions are answered by reading chunks from the saved file
  instead of re-running `find`.

For an MCP smoke test, ask the agent to call an MCP tool that returns large
JSON (e.g. a `list_repos` or `search` style tool). You should see the agent
receive ONLY the index — raw output replaced.

```bash
ls -la ~/.cursor/tool-results/
```

---

## Configuration (optional)

```bash
# ~/.zshrc or ~/.bashrc
export INDEXER_THRESHOLD_TOKENS=2000
export INDEXER_MODEL=qwen3.5:4b
export OLLAMA_URL=http://localhost:11434
export INDEXER_RESULTS_DIR=~/.cursor/tool-results
export INDEXER_OLLAMA_TIMEOUT_SEC=120
```

---

## How the agent retrieves chunks

When the agent sees an index block like:

```
Output too large (~5400 tokens). Saved and indexed.

Summary: Listing of dylib files under /usr/lib, grouped by subsystem.
File: /Users/.../tool-results/conv-abc/Shell_20260515T103210_a1b2c3d4.txt

Chunks:
  [1] lines 1-23   | core libs    — base C runtime libraries
  [2] lines 24-67  | crypto libs  — OpenSSL/CommonCrypto family
  [3] lines 68-120 | graphics     — CoreGraphics / Metal
  ...
```

…it fetches chunk 2 by asking the shell tool to run:

```bash
sed -n '24,67p' /Users/.../tool-results/conv-abc/Shell_20260515T103210_a1b2c3d4.txt
```

The wrapper deliberately bypasses indexing for `sed -n '<a>,<b>p'` Shell
commands so chunk retrieval works without recursive self-indexing.

---

## Troubleshooting

**Hook not firing:**
- Validate JSON: `jq . ~/.cursor/hooks.json`
- Check the path resolves: `ls ~/.cursor/hooks/indexer_cursor.py`
- Cursor logs hook errors to its developer console (`Help → Toggle Developer
  Tools → Console`).

**MCP tools still show raw output:**
- Confirm `tool_name` starts with `MCP:` in the saved `*_hook_output.json`.
  If Cursor reports a different prefix in your version, adjust the
  `tool_name.startswith("MCP:")` branch in `indexer_cursor.py`.

**Shell tool output not replaced:**
- This is expected. Cursor's `postToolUse` contract does not let a hook
  strip raw Shell output. Use the saved file + chunk reads on follow-up
  turns to recover the cost. If you need first-turn replacement, the only
  knobs are `permission: "deny"` on `beforeShellExecution` (too blunt) or
  `updated_mcp_tool_output` on MCP tools (already in use here).

**"connection refused" from Ollama:**
- `ollama serve` (or `brew services start ollama`).

**Hook error → passes through:**
- Intentional fail-open. Check
  `~/.cursor/tool-results/<conversation_id>/*_hook_error.json` for the
  captured error type and message.

**Threshold tuning:**
- Lower `INDEXER_THRESHOLD_TOKENS` for aggressive indexing on smaller
  outputs; raise it if Ollama latency dominates turn time.
