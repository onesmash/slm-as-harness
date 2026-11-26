import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const RUNNER = join(HERE, "check-examples.mjs");

// 造一个技能根：只有 examples/<name>/run.sh 是脚本判断的依据。
function makeRoot(examples) {
  const root = mkdtempSync(join(tmpdir(), "vdi-ex-"));
  mkdirSync(join(root, "examples"), { recursive: true });
  for (const [name, body] of Object.entries(examples)) {
    mkdirSync(join(root, "examples", name), { recursive: true });
    writeFileSync(join(root, "examples", name, "run.sh"), body, { mode: 0o755 });
  }
  return root;
}

function run(root) {
  const r = spawnSync(process.execPath, [RUNNER, root], { encoding: "utf8" });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* 解析失败留给断言报 */ }
  return { code: r.status, json, stderr: r.stderr };
}

test("全部通过时 exit 0，且逐条 PASS", () => {
  const root = makeRoot({
    a: "#!/bin/bash\necho ok-a\nexit 0\n",
    b: "#!/bin/bash\necho ok-b\nexit 0\n",
  });
  try {
    const { code, json } = run(root);
    assert.equal(code, 0);
    assert.equal(json.verdict, "OK");
    assert.deepEqual(json.examples.map((e) => e.state), ["PASS", "PASS"]);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("任一条失败时 exit 1，并指名是哪一条", () => {
  const root = makeRoot({
    good: "#!/bin/bash\nexit 0\n",
    bad: "#!/bin/bash\necho boom >&2\nexit 1\n",
  });
  try {
    const { code, json } = run(root);
    assert.equal(code, 1);
    assert.equal(json.verdict, "FAIL");
    assert.equal(json.examples.find((e) => e.name === "bad").state, "FAIL");
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("run.sh 退出 2 是「未判定」，不许算通过", () => {
  const root = makeRoot({ undecided: "#!/bin/bash\necho 未判定：缺 jar >&2\nexit 2\n" });
  try {
    const { code, json } = run(root);
    assert.equal(code, 2);
    assert.equal(json.verdict, "UNDECIDED");
    assert.equal(json.examples[0].state, "UNDECIDED");
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("零个示例不算通过（空输入必须 REJECT）", () => {
  const root = makeRoot({});
  try {
    const { code, json } = run(root);
    assert.equal(code, 2);
    assert.equal(json.verdict, "UNDECIDED");
    assert.equal(json.examples.length, 0);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("examples/ 目录不存在时也是未判定，不是通过", () => {
  const root = mkdtempSync(join(tmpdir(), "vdi-ex-"));
  try {
    const { code, json } = run(root);
    assert.equal(code, 2);
    assert.equal(json.verdict, "UNDECIDED");
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("示例目录缺 run.sh 是未判定，并指名是哪一条（不许静默跳过）", () => {
  const root = makeRoot({ ok: "#!/bin/bash\nexit 0\n" });
  try {
    // 造一个只有 README、没有 run.sh 的示例目录
    mkdirSync(join(root, "examples", "no-runner"), { recursive: true });
    writeFileSync(join(root, "examples", "no-runner", "README.md"), "# 没有 runner\n");
    const { code, json } = run(root);
    assert.equal(code, 2);
    assert.equal(json.verdict, "UNDECIDED");
    const e = json.examples.find((x) => x.name === "no-runner");
    assert.equal(e.state, "UNDECIDED");
    assert.match(e.reason, /run\.sh/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
