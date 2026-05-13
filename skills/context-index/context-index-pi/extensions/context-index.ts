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
const LIB_SCRIPT = path.join(__dirname, "lib_indexer.py");
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
          new Error(
            `indexer_pi.py exited with code ${code}: ${stderr.slice(0, 500)}`
          )
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
        reject(
          new Error(`Failed to parse indexer output: ${stdout.slice(0, 200)}`)
        );
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

    // 3. Extract text and check threshold — all in TypeScript, no Python overhead
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
