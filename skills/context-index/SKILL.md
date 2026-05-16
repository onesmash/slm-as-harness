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
2. **Claude Code or Cursor**: If your system prompt identifies you as "Claude Code" (Anthropic's official CLI), or the user mentions Claude Code / `claude` CLI / `code.claude.com` / Cursor / `cursor.com` / "Composer" / "Cmd+K agent", route to the Claude Code sub-skill. Cursor's hook system is compatible with Claude Code's hook schema, so the same sub-skill installs on both — just adjust the settings file path and results dir as noted there.
3. **Codex CLI**: If `codex --version` succeeds or the user mentions Codex/OpenAI Codex, route to the Codex sub-skill.
4. **Ambiguous**: If multiple or none are detected, ask the user which platform they're using.

## Sub-Skills

Once the platform is determined, read the corresponding sub-skill's `SKILL.md` and follow its
instructions:

| Platform           | Sub-Skill                                                              | Mechanism                                              |
|--------------------|------------------------------------------------------------------------|--------------------------------------------------------|
| Codex CLI          | [context-index-codex/SKILL.md](context-index-codex/SKILL.md)           | PostToolUse hook (`~/.codex/hooks/`)                   |
| Claude Code, Cursor | [context-index-claudecode/SKILL.md](context-index-claudecode/SKILL.md) | PostToolUse hook in `~/.claude/settings.json` (Claude Code) or `~/.cursor/hooks.json` (Cursor — same schema) |
| pi                 | [context-index-pi/SKILL.md](context-index-pi/SKILL.md)                 | pi extension (`tool_result` event)                     |

## Shared Engine

Both sub-skills share the pure indexing logic in `scripts/lib_indexer.py` (token estimation,
Ollama chat, semantic chunk building, file saving). Each platform has its own thin wrapper
that adapts the shared library to platform-specific I/O conventions:

`lib_indexer.py` saves the original raw output unchanged, but sends the model an
index-only view where each document line is prefixed with `L<number>:`. Tool and
command metadata are sent separately as context, not mixed into the document body,
so model-produced `line_start` / `line_end` values map back to the saved raw file.

| Script                            | Platform           | Role                                                                                                                                                            |
|-----------------------------------|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scripts/lib_indexer.py`          | Shared             | Pure indexing logic (imported by all wrappers)                                                                                                                  |
| `scripts/indexer_codex.py`        | Codex              | Reads Codex hook JSON from stdin, writes `{continue, stopReason}` to stdout                                                                                     |
| `scripts/indexer_claudecode.py`   | Claude Code, Cursor | Reads Claude Code PostToolUse JSON from stdin, writes `{hookSpecificOutput: {updatedToolOutput}}` to stdout. Cursor's hook system accepts the same schema, so it reuses this wrapper. |
| `scripts/indexer_pi.py`           | pi                 | Reads `{content, tool_name, output_dir}` JSON from stdin, writes `{summary, chunks, raw_file}` to stdout                                                        |

The wrappers are thin — skip logic and threshold gating are handled by the platform layer:
- Codex: all skip/threshold logic in `indexer_codex.py`
- Claude Code / Cursor: all skip/threshold logic in `indexer_claudecode.py`
- pi: skip/threshold logic in the TypeScript extension; `indexer_pi.py` only saves and indexes

### Output substitution semantics (platform differences)

The platforms differ in how much of the raw output the hook can hide from the agent:

| Platform    | Can strip raw output from current turn? | Mechanism                                                        |
|-------------|-----------------------------------------|------------------------------------------------------------------|
| Codex       | Yes                                     | `{"continue": false, "stopReason": <index>}` replaces            |
| pi          | Yes                                     | Extension return value replaces `content` array                  |
| Claude Code | Yes                                     | `hookSpecificOutput.updatedToolOutput` replaces tool_response    |
| Cursor      | Yes                                     | Same as Claude Code (`updatedToolOutput`) — Cursor accepts Claude Code's hook schema |

All four platforms now support full first-turn replacement of large tool
outputs with a compact index. Saved raw outputs remain on disk for precise
follow-up retrieval via line-offset reads.

## Configuration (both platforms)

| Variable | Default | Description |
|----------|---------|-------------|
| `INDEXER_THRESHOLD_TOKENS` | `2000` | Min tokens to trigger indexing (~6000 chars) |
| `INDEXER_MODEL` | `qwen3.5:4b` | Ollama model for indexing |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API base URL |
| `INDEXER_RESULTS_DIR` | platform-specific | Where raw outputs are saved (`~/.codex/tool-results`, `~/.claude/tool-results`, `~/.cursor/tool-results`, or `~/.pi/tool-results`) |
| `INDEXER_OLLAMA_TIMEOUT_SEC` | `120` | Ollama call timeout in seconds |
