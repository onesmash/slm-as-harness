// 两个守卫核对器（check-paths / check-portability）的行为测试。
//
// 为什么补这个文件：这两个核对器是试点第四、五轮「摩擦 → 结构」的产物，
// 当时只留下手工实测记录（references/pilot-findings.md 第 52/65 行的「双向实测」「六向实测」），
// 没有一个测试文件。规则在、记录在、锁不在——改一次实现就可能静默失效，而全仓库全绿。
//
// 跑：node --test scripts/check-guards.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const PATHS = join(HERE, "check-paths.mjs");
const PORT = join(HERE, "check-portability.mjs");

// 身份路径在测试里也不写真实用户名，用拼装避免本文件自己变成「写死了某人」
const IDENTITY = "/Users/" + "alice";
const HOMEY = "~" + "/tools/tla";

function run(script, root, extra = []) {
  const r = spawnSync("node", [script, root, ...extra], { encoding: "utf8" });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* 交给断言报空输出 */ }
  return { code: r.status, json, out: r.stdout, err: r.stderr };
}

function tmp(prefix) {
  return mkdtempSync(join(tmpdir(), prefix));
}

function writeAttached(dir, files) {
  for (const [rel, body] of Object.entries(files)) {
    const p = join(dir, rel);
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, body);
  }
}

// ---------------- check-paths ----------------

test("check-paths：引用全部解析 → exit 0，且先报候选数", () => {
  const dir = tmp("paths-ok-");
  writeAttached(dir, {
    "SKILL.md": "# 技能\n\n见 `references/a.md` 与 `templates/t.md`。\n",
    "references/a.md": "# a\n",
    "templates/t.md": "# t\n",
  });
  const r = run(PATHS, dir);
  assert.equal(r.code, 0, `期望 exit 0，得到 ${r.code}；输出 ${r.out}`);
  assert.equal(r.json.verdict, "OK");
  assert.ok(r.json.candidates >= 2, `候选数应 >=2，得到 ${r.json.candidates}`);
  rmSync(dir, { recursive: true, force: true });
});

test("check-paths：断链 → exit 1，并指出是哪一条", () => {
  const dir = tmp("paths-miss-");
  writeAttached(dir, {
    "SKILL.md": "# 技能\n\n见 `references/gone.md`。\n",
    "references/a.md": "# a（没人引用 → 孤儿，也会让结论变红）\n",
  });
  const r = run(PATHS, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /gone\.md/);
  rmSync(dir, { recursive: true, force: true });
});

test("check-paths：references 下有没人引用的文档 → exit 1（孤儿等于不存在）", () => {
  const dir = tmp("paths-orphan-");
  writeAttached(dir, {
    "SKILL.md": "# 技能\n\n见 `references/a.md`。\n",
    "references/a.md": "# a\n",
    "references/extra.md": "# extra（没有任何地方引用它）\n",
  });
  const r = run(PATHS, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /extra\.md/);
  rmSync(dir, { recursive: true, force: true });
});

test("check-paths：零候选 → exit 2（未校验，不是通过）", () => {
  const dir = tmp("paths-zero-");
  writeAttached(dir, { "SKILL.md": "# 技能\n\n纯散文，没有任何反引号路径。\n" });
  const r = run(PATHS, dir);
  assert.equal(r.code, 2, `期望 exit 2，得到 ${r.code}；输出 ${r.out}`);
  assert.equal(r.json.verdict, "UNVERIFIED");
  assert.equal(r.json.candidates, 0);
  rmSync(dir, { recursive: true, force: true });
});

test("check-paths：见下「标题」指路悬空 → exit 1", () => {
  const dir = tmp("paths-anchor-");
  writeAttached(dir, {
    "SKILL.md": "# 技能\n\n见下「根本不存在的小节」。\n\n见 `references/a.md`。\n",
    "references/a.md": "# a\n",
  });
  const r = run(PATHS, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /不存在的小节/);
  rmSync(dir, { recursive: true, force: true });
});

// ---------------- check-portability ----------------

test("check-portability：身份路径无论在哪都是 ERROR → exit 1", () => {
  const dir = tmp("port-id-");
  writeAttached(dir, { "doc.md": `# 文档\n\n工具装在 ${IDENTITY}/tools 下。\n` });
  const r = run(PORT, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /身份路径/);
  rmSync(dir, { recursive: true, force: true });
});

test("check-portability：命令里写死家目录 / 宿主绝对路径 → exit 1", () => {
  const dir = tmp("port-hosty-");
  writeAttached(dir, {
    "a.md": `# a\n\n\`\`\`sh\nexport JAVA=${HOMEY}/bin/java\n\`\`\`\n`,
    "b.md": `# b\n\n\`\`\`sh\nexport TLA2TOOLS=/opt/tla/tla2tools.jar\n\`\`\`\n`,
  });
  const r = run(PORT, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /命令里写死/);
  rmSync(dir, { recursive: true, force: true });
});

test("check-portability：${VAR:-默认值} 是唯一豁免 → exit 0", () => {
  const dir = tmp("port-exempt-");
  writeAttached(dir, {
    "a.md": "# a\n\n```sh\nexport TLA2TOOLS=${TLA2TOOLS:-/opt/tla/tla2tools.jar}\n```\n",
  });
  const r = run(PORT, dir);
  assert.equal(r.code, 0, `期望 exit 0，得到 ${r.code}；输出 ${r.out}`);
  rmSync(dir, { recursive: true, force: true });
});

test("check-portability：散文里的本机路径默认只 WARN，--strict 才算失败", () => {
  const dir = tmp("port-prose-");
  writeAttached(dir, { "a.md": `# a\n\n我把 jar 放在 ${HOMEY} 下。\n` });
  const r1 = run(PORT, dir);
  assert.equal(r1.code, 0, `默认应 exit 0，得到 ${r1.code}；输出 ${r1.out}`);
  assert.match(r1.out, /本机路径/);
  const r2 = run(PORT, dir, ["--strict"]);
  assert.equal(r2.code, 1, `--strict 应 exit 1，得到 ${r2.code}；输出 ${r2.out}`);
  rmSync(dir, { recursive: true, force: true });
});

test("check-portability：标了「本机/已实测」的段落允许本机事实 → exit 0", () => {
  const dir = tmp("port-marked-");
  writeAttached(dir, { "a.md": `# a（本机快照）\n\n## 本机取值\n\njar 在 ${HOMEY} 下。\n` });
  const r = run(PORT, dir);
  assert.equal(r.code, 0, `标记段落应放行，得到 ${r.code}；输出 ${r.out}`);
  assert.doesNotMatch(r.out, /本机路径/);
  rmSync(dir, { recursive: true, force: true });
});

test("check-portability：没扫到任何 md → exit 2（未校验）", () => {
  const dir = tmp("port-none-");
  writeFileSync(join(dir, "notes.txt"), "不是 markdown\n");
  const r = run(PORT, dir);
  assert.equal(r.code, 2, `期望 exit 2，得到 ${r.code}；输出 ${r.out}`);
  assert.equal(r.json.verdict, "UNVERIFIED");
  rmSync(dir, { recursive: true, force: true });
});
