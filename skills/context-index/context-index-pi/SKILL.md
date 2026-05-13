---
name: context-index-pi
description: >
  Install the Context Index extension for pi — a tool_result event handler that intercepts
  large tool outputs, saves them to disk, indexes them with a local small model (qwen3.5:4b
  via Ollama), and returns a summary + chunk index to the agent instead of the raw output.
  This cuts token usage ~70-80% on large Bash/MCP results while preserving precise
  retrieval via offset/limit reads.

  Use this skill when the user is on pi and wants to install the context-index extension,
  or when the main context-index skill routes to this sub-skill for pi setup.
---

# Context Index Extension — pi

> This is a sub-skill of `context-index`. It installs the `tool_result` event handler extension for pi.

## Prerequisite: shared engine

The Python scripts live in the parent skill's `scripts/` directory. Both `lib_indexer.py`
(shared library) and `indexer_pi.py` (pi wrapper) must be copied together into the
extension directory:

```bash
# From this sub-skill's directory, go up one level
PARENT_SKILL_DIR="<path-to-skills>/context-index"
ls "$PARENT_SKILL_DIR/scripts/lib_indexer.py"   # shared library
ls "$PARENT_SKILL_DIR/scripts/indexer_pi.py"     # pi wrapper
```

## What this installs

A pi extension at `~/.pi/agent/extensions/context-index/` that:

1. Listens to the `tool_result` event (fires after every tool execution)
2. If the text output exceeds the token threshold (default: 2000 tokens ≈ 6000 chars), saves raw output to `~/.pi/tool-results/<session>/`
3. Calls `python3 indexer_pi.py` with the output data to get a semantic chunk index from qwen3.5:4b (Ollama)
4. Returns a compact summary + chunk table to the main agent, replacing the raw output
5. Agent retrieves specific chunks via `read` with `offset=<line_start> limit=<lines>`

**Fails open**: any error (Ollama down, model missing, subprocess timeout) → handler returns `undefined` → original output passes through unchanged.

---

## Step 1 — Check prerequisites

```bash
# Python 3.8+
python3 --version

# Node.js (for pi extension)
node --version

# pi itself
pi --version 2>/dev/null || echo "pi may not be on PATH — that's OK if running interactively"
```

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

## Step 4 — Create the extension directory and copy files

```bash
# Create the extension directory
mkdir -p ~/.pi/agent/extensions/context-index

# Copy both Python scripts from the skill
cp <PARENT_SKILL_DIR>/scripts/lib_indexer.py ~/.pi/agent/extensions/context-index/lib_indexer.py
cp <PARENT_SKILL_DIR>/scripts/indexer_pi.py ~/.pi/agent/extensions/context-index/indexer_pi.py
chmod +x ~/.pi/agent/extensions/context-index/indexer_pi.py
```

---

## Step 5 — Write the extension

Write the following TypeScript extension to `~/.pi/agent/extensions/context-index/index.ts`:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { spawn } from "node:child_process";
import * as path from "node:path";
import * as os from "node:os";

// ── Config ──────────────────────────────────────────────────────────────
const THRESHOLD_TOKENS = parseInt(
  process.env.INDEXER_THRESHOLD_TOKENS || "2000",
  10
);
const CHARS_PER_TOKEN = 3;
const INDEXER_SCRIPT = path.join(__dirname, "indexer_pi.py");
const INDEXER_TIMEOUT_MS = parseInt(
  process.env.INDEXER_OLLAMA_TIMEOUT_SEC || "120",
  10
) * 1000;

// pi built-in tools that never produce large text output worth indexing
const SKIP_TOOLS = new Set([
  "read",
  "edit",
  "write",
]);

// ── Helpers ─────────────────────────────────────────────────────────────

function estimateTokens(text: string): number {
  return Math.floor(text.length / CHARS_PER_TOKEN);
}

/** Extract a plain string from pi's tool_result content array */
function contentToText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return (content as Array<{ type: string; text?: string }>)
      .filter((c) => c.type === "text")
      .map((c) => c.text ?? "")
      .join("\n");
  }
  if (content && typeof content === "object") {
    return JSON.stringify(content);
  }
  return String(content ?? "");
}

function isSedRetrieval(toolName: string, input: unknown): boolean {
  if (toolName !== "bash") return false;
  const cmd =
    typeof (input as Record<string, unknown>)?.command === "string"
      ? ((input as Record<string, string>).command ?? "")
      : "";
  return /(?:^|[;&|() \t])sed\s+-n(?:\s|$)/.test(cmd);
}

// ── Indexer subprocess ──────────────────────────────────────────────────

interface IndexerInput {
  content: string;
  tool_name: string;
  tool_input: unknown;
  output_dir: string;
  session_id: string;
}

interface IndexerOutput {
  action: "pass_through" | "indexed" | "error";
  token_count: number;
  // indexed
  index?: {
    summary: string;
    chunks: Array<{
      id: number;
      topic: string;
      summary: string;
      line_start: number;
      line_end: number;
    }>;
  };
  raw_file?: string;
  formatted?: string;
  // error
  error?: string;
  error_type?: string;
}

function runIndexer(input: IndexerInput): Promise<IndexerOutput> {
  return new Promise((resolve, reject) => {
    // Run from the directory containing indexer_pi.py so lib_indexer.py is importable
    const proc = spawn("python3", [INDEXER_SCRIPT], {
      cwd: __dirname,
      stdio: ["pipe", "pipe", "pipe"],
      timeout: INDEXER_TIMEOUT_MS,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d: Buffer) => {
      stdout += d.toString();
    });
    proc.stderr.on("data", (d: Buffer) => {
      stderr += d.toString();
    });

    proc.on("close", (code: number | null) => {
      if (code !== 0) {
        reject(
          new Error(`indexer exited with code ${code}: ${stderr.slice(0, 500)}`)
        );
        return;
      }
      try {
        const parsed = JSON.parse(stdout) as IndexerOutput;
        if (parsed.error) {
          reject(new Error(parsed.error));
          return;
        }
        resolve(parsed);
      } catch {
        reject(new Error(`Failed to parse indexer output: ${stdout.slice(0, 200)}`));
      }
    });

    proc.on("error", reject);
    proc.stdin.write(JSON.stringify(input));
    proc.stdin.end();
  });
}

// ── Extension ───────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  pi.on("tool_result", async (event, ctx) => {
    // 1. Skip tools whose output is never large
    if (SKIP_TOOLS.has(event.toolName)) return;

    // 2. Skip sed -n chunk-retrieval reads (avoid recursive indexing)
    if (isSedRetrieval(event.toolName, event.input)) return;

    // 3. Extract text and check threshold
    const text = contentToText(event.content);
    if (!text) return;

    const tokenEstimate = estimateTokens(text);
    if (tokenEstimate < THRESHOLD_TOKENS) return;

    // 4. Call indexer_pi.py (saves file + calls Ollama for semantic index)
    try {
      const result = await runIndexer({
        content: text,
        tool_name: event.toolName,
        tool_input: event.input ?? {},
        output_dir: path.join(
          os.homedir(),
          process.env.INDEXER_RESULTS_DIR || ".pi/tool-results"
        ),
        session_id: process.env.PI_SESSION_ID || "pi-session",
      });

      // If below threshold or error, let original output pass through
      if (result.action !== "indexed" || !result.formatted) return;

      // 5. Replace tool result with indexed summary
      return {
        content: [{ type: "text", text: result.formatted }],
      };
    } catch (err) {
      // Fail open: log and let original output pass through
      console.error(
        "[context-index] Indexer error (passing through original output):",
        err instanceof Error ? err.message : err
      );
    }
    // No return → original output passes through unchanged
  });
}
```

---

## Step 6 — Reload or restart pi

If pi is running interactively, trigger reload:

```
/reload
```

Or restart pi. The extension will be auto-discovered from `~/.pi/agent/extensions/context-index/index.ts`.

---

## Step 7 — Smoke test

Run a command that produces large output and verify the indexer fires:

```bash
# If using pi interactively, ask the agent to run:
find /usr/lib -name '*.dylib' 2>/dev/null | head -100
```

Expected behavior:
- Extension intercepts the large output
- Agent receives index format instead of raw output:
  ```
  Output too large (~N tokens). Saved and indexed.
  Summary: ...
  File: ~/.pi/tool-results/<session>/Bash_...txt
  Chunks:
    [1] lines X-Y | <topic> — <summary>
    ...
  ```

Check saved results:
```bash
ls -la ~/.pi/tool-results/
```

---

## Configuration (optional)

Set in shell profile (`~/.zshrc` or `~/.bashrc`) before starting pi:

```bash
export INDEXER_THRESHOLD_TOKENS=2000   # only index very large outputs
export INDEXER_MODEL=qwen3.5:4b       # pin explicit model
export OLLAMA_URL=http://localhost:11434  # Ollama endpoint
export INDEXER_RESULTS_DIR=~/.pi/tool-results  # output storage
```

---

## How the agent retrieves chunks

When the agent receives an indexed result, it uses pi's `read` tool with offset/limit to fetch specific chunks:

```
read path="~/.pi/tool-results/<session>/Bash_<ts>_<hash>.txt" offset=45 limit=45
```

This reads the chunk spanning lines 45-89 (45 lines starting at offset 45). The extension deliberately skips indexing for `sed -n` commands so that chunk retrieval works without recursive indexing.

---

## Troubleshooting

**Extension not loading:**
- Check the file exists: `ls -la ~/.pi/agent/extensions/context-index/index.ts`
- Check pi logs for extension errors
- Run `/reload` in pi interactive mode
- Verify both Python scripts are next to `index.ts`: `ls -la ~/.pi/agent/extensions/context-index/lib_indexer.py ~/.pi/agent/extensions/context-index/indexer_pi.py`

**"connection refused" from Ollama:**
- Start Ollama: `ollama serve` (or `brew services start ollama`)
- Check: `curl http://localhost:11434/api/tags`

**Model not found:**
- Re-pull: `ollama pull qwen3.5:4b`
- List available: `ollama list`

**Extension error → passes through:**
- This is intentional fail-open behavior. The agent continues with the raw output.
- Check pi's stderr for error messages (they include `[context-index]` prefix)
