---
name: context-index-codex
description: >
  Install the Context Index hook for Codex CLI — a PostToolUse hook that intercepts
  large tool outputs, saves them to disk, indexes them with a local small model (qwen3.5:4b
  via Ollama), and returns a summary + chunk index to the main agent instead of the raw
  output. This cuts token usage ~70-80% on large Bash/MCP results.

  Use this skill when the user is on Codex CLI and wants to install the context-index hook,
  or when the main context-index skill routes to this sub-skill for Codex setup.
---

# Context Index Hook — Codex CLI

> This is a sub-skill of `context-index`. It installs the PostToolUse hook for Codex CLI.

## Prerequisite: shared engine

The Python scripts live in the parent skill's `scripts/` directory. Both `lib_indexer.py`
(shared library) and `indexer_codex.py` (Codex wrapper) must be copied together:

```bash
# The parent skill dir is the directory containing this sub-skill
PARENT=$(dirname "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$PWD")")")
ls "$PARENT/scripts/lib_indexer.py"   # shared library
ls "$PARENT/scripts/indexer_codex.py"  # Codex wrapper
```

If the path can't be resolved this way, search under the `skills/context-index/` tree.

## What this installs

A `PostToolUse` hook for [Codex CLI](https://github.com/openai/codex) that:

1. Intercepts `Bash` and `mcp__*` tool results after every call
2. If output exceeds the token threshold (default: 2000 tokens ≈ 6000 chars), saves raw output to `~/.codex/tool-results/<session_id>/`
3. Calls a local `qwen3.5:4b` model via Ollama to produce a semantic chunk index
4. Returns a compact summary + chunk table to the main agent, replacing the raw output
5. Agent retrieves specific chunks via `sed -n '<start>,<end>p' <file>` when needed

**Fails open**: any error (Ollama down, model missing, timeout) → hook exits 0 → original output passes through unchanged.

---

## Step 1 — Check prerequisites

```bash
# Codex CLI
codex --version

# Python 3.8+
python3 --version
```

If `codex` is not found, install it first: `npm install -g @openai/codex`

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

Expected output: `qwen3.5:4b   <size>`

---

## Step 4 — Install the hook scripts

Copy both `lib_indexer.py` and `indexer_codex.py` from the parent skill to `~/.codex/hooks/`:

```bash
mkdir -p ~/.codex/hooks
cp <PARENT_SKILL_DIR>/scripts/lib_indexer.py ~/.codex/hooks/lib_indexer.py
cp <PARENT_SKILL_DIR>/scripts/indexer_codex.py ~/.codex/hooks/indexer_codex.py
chmod +x ~/.codex/hooks/indexer_codex.py
```

Verify:
```bash
ls -la ~/.codex/hooks/lib_indexer.py ~/.codex/hooks/indexer_codex.py
python3 ~/.codex/hooks/indexer_codex.py --help 2>/dev/null || echo "Script installed (no --help flag, that's OK)"
```

---

## Step 5 — Configure hooks.json

Create or update `~/.codex/hooks.json`:

```bash
cat > ~/.codex/hooks.json << 'EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "^(?:[^R].*|R[^e].*|Re[^a].*|Rea[^d].*|Read.+|R|Re|Rea)$",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.codex/hooks/indexer_codex.py",
            "timeout": 120,
            "statusMessage": "Indexing large output..."
          }
        ]
      }
    ]
  }
}
EOF
```

If `~/.codex/hooks.json` already exists and has other hooks, merge manually — add the `PostToolUse` block alongside existing entries.

---

## Step 6 — Enable hooks in config.toml

Check if `~/.codex/config.toml` exists:
```bash
cat ~/.codex/config.toml 2>/dev/null || echo "(file does not exist yet)"
```

If it exists and has a `[features]` section, add `codex_hooks = true` to it:
```bash
grep -n '\[features\]' ~/.codex/config.toml
```

**If `[features]` section exists**, add the line after it:
```bash
sed -i '' '/\[features\]/a\ncodex_hooks = true' ~/.codex/config.toml
```

**If `[features]` section does NOT exist**, append it:
```bash
cat >> ~/.codex/config.toml << 'EOF'

[features]
codex_hooks = true
EOF
```

**If config.toml doesn't exist**, create it:
```bash
cat > ~/.codex/config.toml << 'EOF'
[features]
codex_hooks = true
EOF
```

Verify:
```bash
grep -A2 '\[features\]' ~/.codex/config.toml
```

---

## Step 7 — Smoke test

Run a quick test to confirm the hook fires:

```bash
INDEXER_THRESHOLD_TOKENS=100 codex exec --skip-git-repo-check \
  "run: find /usr/lib -name '*.dylib' 2>/dev/null | head -100"
```

Expected behavior:
- Hook fires: `Indexing large output...` status appears
- Main agent receives index format instead of raw output:
  ```
  Output too large (~N tokens). Saved and indexed.
  Summary: ...
  File: ~/.codex/tool-results/<session>/Bash_...txt
  Chunks:
    [1] lines X-Y | <topic> — <summary>
    ...
  ```

Check saved results:
```bash
ls -la ~/.codex/tool-results/
```

---

## Configuration (optional)

Set in shell profile to customize:
```bash
# ~/.zshrc or ~/.bashrc
export INDEXER_THRESHOLD_TOKENS=2000
export INDEXER_MODEL=qwen3.5:4b
```

---

## How the agent retrieves chunks

When the main agent receives an indexed result, it uses line-range reads to fetch specific chunks:

```bash
sed -n '45,89p' ~/.codex/tool-results/<session>/Bash_<ts>_<hash>.txt
```

The hook deliberately bypasses indexing only for explicit `sed -n` chunk-retrieval reads to avoid recursive self-indexing.

---

## Troubleshooting

**Hook not firing:**
- Confirm `codex_hooks = true` is set in `~/.codex/config.toml` under `[features]`
- Confirm `~/.codex/hooks.json` exists and has `PostToolUse` configured
- Run `codex` with a large-output command and watch for `Indexing large output...`

**"connection refused" from Ollama:**
- Start Ollama: `ollama serve` (or `brew services start ollama` for background service)
- Check: `curl http://localhost:11434/api/tags`

**Model not found:**
- Re-pull: `ollama pull qwen3.5:4b`
- List available: `ollama list`

**Hook error → passes through:**
- This is intentional fail-open behavior
- Check Python errors: `echo '{"tool_name":"test","tool_input":{},"tool_response":"x","session_id":"test"}' | python3 ~/.codex/hooks/indexer_codex.py`

**WebSearch tool not indexed:**
- Known limitation: Codex `PostToolUse` hook does not fire for the built-in WebSearch tool. Only `Bash` and `mcp__*` tools are interceptable.
