#!/usr/bin/env node
// 技能内示例的机器核对器：把「示例还能跑」从人眼变成退出码。
//
// 用法：node check-examples.mjs [SKILL_ROOT]
//   默认 SKILL_ROOT = 本脚本所在目录的上一级。
//
// 判据与 run.sh 的三态约定一致（见 references/toolchain.md 与各示例 README）：
//   0 = PASS      示例自证通过（守住 + 破坏变体按预期报红）
//   1 = FAIL      示例不符预期
//   2 = UNDECIDED 缺 Java / 缺 jar / 超时——未判定，不许算通过
//
// 三态聚合：任一条 FAIL ⟹ 1；否则任一条 UNDECIDED 或零个示例 ⟹ 2；全 PASS ⟹ 0。
// 零样本一律报 UNDECIDED：没有示例可跑时，「全部通过」是空话（#d1db 的同款教训）。

import { readdirSync, existsSync, statSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = process.argv[2] || dirname(HERE);
const EXAMPLES_DIR = join(ROOT, "examples");
const TIMEOUT_MS = Number(process.env.VDI_EXAMPLE_TIMEOUT_MS || 300000);

function discover() {
  if (!existsSync(EXAMPLES_DIR) || !statSync(EXAMPLES_DIR).isDirectory()) return [];
  return readdirSync(EXAMPLES_DIR)
    .filter((name) => statSync(join(EXAMPLES_DIR, name)).isDirectory())
    .sort();
}

function stateOf(rc) {
  if (rc === 0) return "PASS";
  if (rc === 2) return "UNDECIDED";
  return "FAIL";
}

function runOne(name) {
  const script = join(EXAMPLES_DIR, name, "run.sh");
  // 有示例目录却没有 runner：这是「没人核对」，不是「通过」——按未判定报，并指名道姓。
  if (!existsSync(script)) {
    process.stderr.write(`[UNDECIDED] ${name}: 缺 run.sh（示例没有机器核对入口）\n`);
    return { name, state: "UNDECIDED", rc: "n/a", ms: 0, reason: "缺 run.sh" };
  }
  const started = Date.now();
  // 显式用 bash：示例里用到了 [[ ]] 之外的 bash 特性，且不依赖 run.sh 的执行位。
  const r = spawnSync("bash", [script], {
    encoding: "utf8",
    timeout: TIMEOUT_MS,
    env: process.env,
  });
  const ms = Date.now() - started;
  const rc = r.error && r.error.code === "ETIMEDOUT" ? 2 : r.status;
  const state = stateOf(rc);
  // 未判定/失败的原因留在 stderr，stdout 只留 JSON（调用方要能直接 parse）。
  if (state !== "PASS") {
    const why = (r.stderr || r.stdout || "").trim().split("\n").slice(-3).join(" | ");
    process.stderr.write(`[${state}] ${name}: rc=${rc} ${why}\n`);
  }
  return { name, state, rc: rc === null ? "null" : rc, ms };
}

const names = discover();
const examples = names.map(runOne);
const counts = {
  pass: examples.filter((e) => e.state === "PASS").length,
  fail: examples.filter((e) => e.state === "FAIL").length,
  undecided: examples.filter((e) => e.state === "UNDECIDED").length,
};

let verdict = "OK";
let code = 0;
if (counts.fail > 0) {
  verdict = "FAIL";
  code = 1;
} else if (counts.undecided > 0 || examples.length === 0) {
  verdict = "UNDECIDED";
  code = 2;
}

process.stdout.write(JSON.stringify({
  root: ROOT,
  verdict,
  examples,
  counts,
  note: examples.length === 0 ? "没有 examples/*/run.sh 可跑——零样本不算通过" : undefined,
}, null, 2) + "\n");

process.exit(code);
