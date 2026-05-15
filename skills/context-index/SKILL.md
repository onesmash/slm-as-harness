---
name: context-index
description: >
  Install the Context Index system — a progressive-disclosure mechanism that intercepts
  large tool outputs, saves them to disk, indexes them with a local small model (qwen3.5:4b
  via Ollama), and returns a summary + chunk index to the agent instead of the raw output.
  This cuts token usage ~70-80% on large Bash/MCP results while preserving precise
  retrieval via line-offset reads.

  Use this skill whenever the user wants to install or configure context indexing,
  set up progressive disclosure for agent tool results, reduce token waste on large outputs,
  install the Ollama/qwen3.5 local model for output indexing, or asks why an agent is burning
  too many tokens on command output. Supports Codex CLI, Claude Code, Cursor, and pi platforms.
---

# Context Index

This skill installs a progressive-disclosure system that indexes large tool outputs so the
agent sees summaries instead of raw dumps, cutting token usage ~70-80%.

It works on two platforms. Detect which one the user is using, then route accordingly.

## Platform Detection

Check these in order:

1. **pi**: If pi is the running agent (check your system prompt — does it mention "pi coding agent"?) or the user explicitly says "pi", route to the pi sub-skill.
2. **Claude Code**: If your system prompt identifies you as "Claude Code" (Anthropic's official CLI), or the user mentions Claude Code / `claude` CLI / `code.claude.com`, route to the Claude Code sub-skill.
3. **Cursor**: If the user mentions Cursor / `cursor.com` / the Cursor editor / "Composer" / "Cmd+K agent", route to the Cursor sub-skill.
4. **Codex CLI**: If `codex --version` succeeds or the user mentions Codex/OpenAI Codex, route to the Codex sub-skill.
5. **Ambiguous**: If multiple or none are detected, ask the user which platform they're using.

## Sub-Skills

Once the platform is determined, read the corresponding sub-skill's `SKILL.md` and follow its
instructions:

| Platform    | Sub-Skill                                                              | Mechanism                                              |
|-------------|------------------------------------------------------------------------|--------------------------------------------------------|
| Codex CLI   | [context-index-codex/SKILL.md](context-index-codex/SKILL.md)           | PostToolUse hook (`~/.codex/hooks/`)                   |
| Claude Code | [context-index-claudecode/SKILL.md](context-index-claudecode/SKILL.md) | PostToolUse hook in `~/.claude/settings.json`          |
| Cursor      | [context-index-cursor/SKILL.md](context-index-cursor/SKILL.md)         | postToolUse hook in `~/.cursor/hooks.json`             |
| pi          | [context-index-pi/SKILL.md](context-index-pi/SKILL.md)                 | pi extension (`tool_result` event)                     |

## Shared Engine

Both sub-skills share the pure indexing logic in `scripts/lib_indexer.py` (token estimation,
Ollama chat, semantic chunk building, file saving). Each platform has its own thin wrapper
that adapts the shared library to platform-specific I/O conventions:

`lib_indexer.py` saves the original raw output unchanged, but sends the model an
index-only view where each document line is prefixed with `L<number>:`. Tool and
command metadata are sent separately as context, not mixed into the document body,
so model-produced `line_start` / `line_end` values map back to the saved raw file.

| Script                            | Platform    | Role                                                                                                                                                            |
|-----------------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scripts/lib_indexer.py`          | Shared      | Pure indexing logic (imported by all wrappers)                                                                                                                  |
| `scripts/indexer_codex.py`        | Codex       | Reads Codex hook JSON from stdin, writes `{continue, stopReason}` to stdout                                                                                     |
| `scripts/indexer_claudecode.py`   | Claude Code | Reads Claude Code PostToolUse JSON from stdin, writes `{hookSpecificOutput: {additionalContext}}` to stdout                                                     |
| `scripts/indexer_cursor.py`       | Cursor      | Reads Cursor postToolUse JSON from stdin; writes `{updated_mcp_tool_output}` for MCP tools or `{additional_context}` for Shell/Grep                             |
| `scripts/indexer_pi.py`           | pi          | Reads `{content, tool_name, output_dir}` JSON from stdin, writes `{summary, chunks, raw_file}` to stdout                                                        |

The wrappers are thin — skip logic and threshold gating are handled by the platform layer:
- Codex: all skip/threshold logic in `indexer_codex.py`
- Claude Code: all skip/threshold logic in `indexer_claudecode.py`
- Cursor: all skip/threshold logic in `indexer_cursor.py`; tool-category branching (MCP replace vs Shell append) inside the wrapper
- pi: skip/threshold logic in the TypeScript extension; `indexer_pi.py` only saves and indexes

### Output substitution semantics (platform differences)

The platforms differ in how much of the raw output the hook can hide from the agent:

| Platform    | Can strip raw output from current turn?                          | Mechanism                                              |
|-------------|------------------------------------------------------------------|--------------------------------------------------------|
| Codex       | Yes                                                              | `{"continue": false, "stopReason": <index>}` replaces  |
| pi          | Yes                                                              | Extension return value replaces `content` array        |
| Cursor      | Yes for MCP tools, no for Shell/Grep                             | `updated_mcp_tool_output` (MCP) / `additional_context` (Shell) |
| Claude Code | No — index is *appended* as `additionalContext`                  | Savings accrue on follow-up turns via `Read offset/limit` on saved file |

The substitution power is dictated by each platform's hook contract, not a
design choice. When the platform can only append (Claude Code; Cursor for
non-MCP), the win comes from follow-up turns: the agent reads chunks from the
saved file instead of re-running the command or re-quoting the raw blob. Set
user expectations accordingly when recommending the install.

## Configuration (both platforms)

| Variable | Default | Description |
|----------|---------|-------------|
| `INDEXER_THRESHOLD_TOKENS` | `2000` | Min tokens to trigger indexing (~6000 chars) |
| `INDEXER_MODEL` | `qwen3.5:4b` | Ollama model for indexing |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API base URL |
| `INDEXER_RESULTS_DIR` | platform-specific | Where raw outputs are saved (`~/.codex/tool-results`, `~/.claude/tool-results`, `~/.cursor/tool-results`, or `~/.pi/tool-results`) |
| `INDEXER_OLLAMA_TIMEOUT_SEC` | `120` | Ollama call timeout in seconds |
