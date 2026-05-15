---
name: context-index-claudecode
description: >
  Install the Context Index hook for Claude Code — a PostToolUse hook that saves
  large tool outputs to disk, indexes them with a local small model (qwen3.5:4b via
  Ollama), and injects a summary + chunk index as additionalContext so the agent
  can later read specific chunks via `Read offset/limit` instead of re-running
  commands or burning tokens re-quoting the raw blob.

  Use this skill when the user is on Claude Code (the CLI from
  code.claude.com) and wants to install the context-index hook, or when the main
  context-index skill routes to this sub-skill for Claude Code setup.
---

# Context Index Hook — Claude Code

> This is a sub-skill of `context-index`. It installs the PostToolUse hook for
> [Claude Code](https://code.claude.com).

## Prerequisite: shared engine

The Python scripts live in the parent skill's `scripts/` directory. Both
`lib_indexer.py` (shared library) and `indexer_claudecode.py` (Claude Code wrapper)
must be copied together:

```bash
# The parent skill dir is the directory containing this sub-skill
PARENT_SKILL_DIR="<path-to-skills>/context-index"
ls "$PARENT_SKILL_DIR/scripts/lib_indexer.py"          # shared library
ls "$PARENT_SKILL_DIR/scripts/indexer_claudecode.py"   # Claude Code wrapper
```

## What this installs

A `PostToolUse` hook (see [Claude Code hooks reference](https://code.claude.com/docs/en/hooks))
that:

1. Fires after every tool call (`Bash`, `Grep`, `Glob`, `WebFetch`, `WebSearch`,
   `Task`, and all `mcp__*` tools). Trivially-small tools (`Edit`, `Write`,
   `Read`, `NotebookEdit`, `TodoWrite`, `ExitPlanMode`) are skipped inside the
   wrapper.
2. If `tool_response` exceeds the token threshold (default: 2000 tokens ≈ 6000
   chars), saves the raw output to `~/.claude/tool-results/<session_id>/`.
3. Calls a local `qwen3.5:4b` model via Ollama to produce a semantic chunk index.
4. Returns the index via `hookSpecificOutput.additionalContext` so Claude sees a
   compact summary + chunk table right after the raw tool output. The index
   points at the saved file and exact line ranges for each chunk.
5. On subsequent turns, the agent fetches just the chunks it needs via
   `Read path="<saved-file>" offset=<line_start> limit=<lines>` instead of
   re-running the command or re-quoting the raw blob.

**Fails open**: any error (Ollama down, model missing, timeout, malformed JSON)
→ wrapper exits 0 with empty stdout → original tool result passes through unchanged.

### Important: how token savings actually accrue here

Claude Code's `PostToolUse` hook cannot strip the raw `tool_response` from the
turn in which it fires — `additionalContext` is *appended after* the tool result,
not substituted for it. So on the **first** turn the agent still pays the full
raw-output cost.

The savings come on **follow-up turns**:

- The agent now knows the output is saved at a specific path with a chunk index.
- Instead of re-running the same command (e.g. running `ls`/`grep`/build twice),
  the agent reads just the relevant chunk by line range.
- Long sessions that would otherwise quote the same large blob across many
  turns instead cite the saved file.

If you want first-turn replacement, you're on the wrong platform — use the Codex
sub-skill (`continue: false` strips the original) or the pi sub-skill (extension
return value replaces the result).

---

## Step 1 — Check prerequisites

```bash
# Claude Code
claude --version

# Python 3.8+
python3 --version
```

If `claude` is not found, install it first (see [code.claude.com/docs](https://code.claude.com/docs)).

---

## Step 2 — Install Ollama

Check if already installed:
```bash
ollama --version
```

If not installed, install via Homebrew (macOS/Linux):
```bash
brew install ollama
```

Or via the official installer script (Linux):
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

After install, start the Ollama service:
```bash
ollama serve &
```

Verify it's running:
```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```

---

## Step 3 — Pull the indexer model

```bash
ollama pull qwen3.5:4b
```

This downloads ~2GB. Verify:
```bash
ollama list | grep qwen3.5
```

---

## Step 4 — Install the hook scripts

Copy both `lib_indexer.py` and `indexer_claudecode.py` from the parent skill to
`~/.claude/hooks/`:

```bash
mkdir -p ~/.claude/hooks
cp <PARENT_SKILL_DIR>/scripts/lib_indexer.py         ~/.claude/hooks/lib_indexer.py
cp <PARENT_SKILL_DIR>/scripts/indexer_claudecode.py  ~/.claude/hooks/indexer_claudecode.py
chmod +x ~/.claude/hooks/indexer_claudecode.py
```

Verify:
```bash
ls -la ~/.claude/hooks/lib_indexer.py ~/.claude/hooks/indexer_claudecode.py
```

Smoke test the wrapper directly (Ollama must be running and the model pulled):

```bash
echo '{
  "tool_name": "Bash",
  "tool_input": {"command": "ls /usr/lib"},
  "tool_response": "'"$(printf 'libfoo.dylib\n%.0s' {1..2000})"'",
  "session_id": "smoke-test"
}' | python3 ~/.claude/hooks/indexer_claudecode.py
```

Expected: a JSON blob with `hookSpecificOutput.additionalContext` containing the
chunk index. If you get empty output, that's pass-through — either the content
was below threshold, the tool was skipped, or an error fell open. Check
`~/.claude/tool-results/smoke-test/` for any saved files and `_hook_error.json`
metadata.

---

## Step 5 — Register the hook in `~/.claude/settings.json`

Claude Code reads hooks from `~/.claude/settings.json` (user-level, all projects),
`.claude/settings.json` (project-level, checked in), or
`.claude/settings.local.json` (project-local, gitignored). Most users want
user-level so it works in every project.

**Check current settings:**
```bash
cat ~/.claude/settings.json 2>/dev/null || echo "(file does not exist yet)"
```

**If the file does NOT exist**, create it:
```bash
cat > ~/.claude/settings.json << 'EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/indexer_claudecode.py",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
EOF
```

**If the file already exists**, merge the `hooks.PostToolUse` block into it.
Easiest way is with `jq`:

```bash
TMP=$(mktemp)
jq '.hooks.PostToolUse = ((.hooks.PostToolUse // []) + [{
  "matcher": "*",
  "hooks": [{
    "type": "command",
    "command": "python3 ~/.claude/hooks/indexer_claudecode.py",
    "timeout": 120
  }]
}])' ~/.claude/settings.json > "$TMP" && mv "$TMP" ~/.claude/settings.json
```

The `"matcher": "*"` fires on every tool call; the wrapper's internal `SKIP_TOOLS`
filter then drops `Edit`/`Write`/`Read`/`NotebookEdit`/`TodoWrite`/`ExitPlanMode`
and `sed -n` chunk reads. If you'd rather scope at the matcher level to skip the
Python invocation entirely on small-output tools, use this regex matcher instead:

```json
"matcher": "^(Bash|Grep|Glob|WebFetch|WebSearch|Task|mcp__.+)$"
```

Verify the config parses:
```bash
jq '.hooks.PostToolUse' ~/.claude/settings.json
```

---

## Step 6 — Restart Claude Code

Settings reload on session start. Quit any running `claude` sessions and start a
fresh one. (You can also use `/hooks` in an interactive session to inspect what
Claude Code has currently loaded — see if your `PostToolUse` entry shows up.)

---

## Step 7 — Smoke test inside Claude Code

In an interactive `claude` session, ask the agent to run a command with large
output, e.g.:

> Run `find /usr/lib -name '*.dylib' 2>/dev/null | head -200` and tell me what
> kinds of libraries are there.

Expected behavior:

- The hook fires after the `Bash` call.
- A file appears under `~/.claude/tool-results/<session_id>/Bash_<ts>_<hash>.txt`.
- The agent sees both the raw output AND an injected `additionalContext` block
  with the chunk index pointing at the saved file.
- If you then ask a follow-up question, the agent should read chunks via `Read
  offset/limit` from the saved file instead of re-running `find`.

Check saved results:
```bash
ls -la ~/.claude/tool-results/
```

---

## Configuration (optional)

Set in your shell profile (`~/.zshrc` / `~/.bashrc`) before starting Claude Code,
or via the `env` block in `~/.claude/settings.json`:

```bash
export INDEXER_THRESHOLD_TOKENS=2000     # min tokens to trigger indexing
export INDEXER_MODEL=qwen3.5:4b          # Ollama model
export OLLAMA_URL=http://localhost:11434
export INDEXER_RESULTS_DIR=~/.claude/tool-results
export INDEXER_OLLAMA_TIMEOUT_SEC=120
```

Using `settings.json` `env` block (works without changing your shell):

```json
{
  "env": {
    "INDEXER_THRESHOLD_TOKENS": "2000",
    "INDEXER_MODEL": "qwen3.5:4b"
  }
}
```

---

## How the agent retrieves chunks

When the agent sees `additionalContext` like:

```
Output too large (~5400 tokens). Saved and indexed.

Summary: Listing of dylib files under /usr/lib, grouped by subsystem.
File: /Users/.../tool-results/abc123/Bash_20260515T103210_a1b2c3d4.txt

Chunks:
  [1] lines 1-23   | core libs            — base C runtime libraries
  [2] lines 24-67  | crypto libs          — OpenSSL/CommonCrypto family
  [3] lines 68-120 | graphics libs        — CoreGraphics / Metal
  ...

Use `Read` with offset=<line_start> limit=<line_end - line_start + 1> to fetch
specific chunks from the saved file. Avoid re-running the original command —
it is already saved at the path above.
```

…it can fetch chunk 2 with:

```
Read path="/Users/.../tool-results/abc123/Bash_20260515T103210_a1b2c3d4.txt"
     offset=24 limit=44
```

The wrapper deliberately skips indexing for `sed -n '<start>,<end>p' <file>`
Bash commands so legacy retrieval scripts work without recursive self-indexing,
but on Claude Code you should prefer the native `Read offset/limit` path —
chunks are loaded as a structured tool call rather than shell parsing.

---

## Troubleshooting

**Hook not firing:**
- Check `/hooks` inside a running `claude` session — does your `PostToolUse`
  entry show up under the "User" source?
- Confirm `~/.claude/settings.json` is valid JSON: `jq . ~/.claude/settings.json`
- Run with verbose logging: `claude --verbose` (or `--debug`) and watch for hook
  execution lines.

**"connection refused" from Ollama:**
- Start Ollama: `ollama serve` (or `brew services start ollama` for a background
  service).
- Check: `curl http://localhost:11434/api/tags`.

**Model not found:**
- Re-pull: `ollama pull qwen3.5:4b`.
- List available: `ollama list`.

**Hook runs but agent still sees only raw output, no index:**
- The hook may have errored and failed open. Look in
  `~/.claude/tool-results/<session>/*_hook_error.json` for the captured error
  type and message.
- Verify the wrapper produces stdout on a manual run (see Step 4 smoke test).

**Agent re-runs commands instead of reading saved chunks:**
- This is a prompting issue, not a hook issue. The `additionalContext` block
  already tells the agent to prefer `Read offset/limit`; if it ignores that,
  consider adding a permanent reminder in your project's `CLAUDE.md`:
  > "When you see an `Output too large` indexed block, fetch chunks via `Read
  > offset/limit` from the saved file path — never re-run the original command."

**Threshold tuning:**
- Default 2000 tokens is conservative. Drop to `INDEXER_THRESHOLD_TOKENS=500`
  for aggressive indexing on small outputs (more Ollama calls, finer chunking).
- Raise to `5000+` if Ollama latency dominates your turn time.
