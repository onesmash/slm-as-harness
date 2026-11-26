// check-register 的行为测试：用真实临时 git 仓库造场景，只看退出码与 JSON 输出。
// 跑：node --test scripts/check-register.test.mjs
//
// 这组测试要守住的东西：
//   ① sync commit 之后覆盖文件有改动 → 必须报错（这正是「通过是对过期描述的通过」）
//   ② 工作区里有未提交改动也算漂移（还没提交不等于没改）
//   ③ 不是 git 仓库 → 明说「未核」，不许静默当通过
//   ④ 一行都没有可解析的覆盖文件 → 「零样本」要单独说，不许报 OK 就完事
//   ⑤ 承诺变更证据列：写不出可核证据 → 报错
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync, spawnSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const CHECKER = join(HERE, "check-register.mjs");

function sh(cwd, args) {
  return execFileSync(args[0], args.slice(1), { cwd, encoding: "utf8" }).trim();
}

function makeRepo() {
  const dir = mkdtempSync(join(tmpdir(), "reg-test-"));
  sh(dir, ["git", "init", "-q"]);
  sh(dir, ["git", "config", "user.email", "t@example.invalid"]);
  sh(dir, ["git", "config", "user.name", "t"]);
  mkdirSync(join(dir, "sources"), { recursive: true });
  writeFileSync(join(dir, "sources", "a.ts"), "export const a = 1;\n");
  writeFileSync(join(dir, "sources", "destruct.mjs"), "// 破坏变体入口\n");
  sh(dir, ["git", "add", "-A"]);
  sh(dir, ["git", "commit", "-q", "-m", "base"]);
  return { dir, base: sh(dir, ["git", "rev-parse", "HEAD"]) };
}

function row({ sync, covered = "`sources/a.ts:1`", status = "守住", promise = "", evidence = "见 `sources/destruct.mjs:1`" } = {}) {
  // 证据命令必须指得到真文件：守住 行写 `node x.mjs` 这种翻不到的名字，机器核对会报红
  return `| P1 | 同一笔钱只扣一次 | me | ${covered} | 单实例 | L2 | ${evidence} | 0 | — | ${status} | ${sync} | ${promise} |`;
}

const HEAD = [
  "| 编号 | 性质（一句话，可被反例证伪） | owner | 覆盖的文件/函数 | 范围 | 证据等级 | 破坏变体 / 证据命令 | 退出码 | S4 日志 | 状态 | sync commit | 承诺变更证据 |",
  "|---|---|---|---|---|---|---|---|---|---|---|---|",
];

function writeRegister(dir, rows) {
  const p = join(dir, "invariants", "property-register.md");
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, ["# 登记表", "", ...HEAD, ...rows, ""].join("\n"));
  return p;
}

function run(register, root, extra = []) {
  const r = spawnSync("node", [CHECKER, register, "--root", root, ...extra], { encoding: "utf8" });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* 保留 null，由断言报出来 */ }
  return { code: r.status, json, out: r.stdout, err: r.stderr };
}

function commitChange(dir, file = "sources/a.ts") {
  writeFileSync(join(dir, file), "export const a = 2;\n");
  sh(dir, ["git", "add", "-A"]);
  sh(dir, ["git", "commit", "-q", "-m", "touch covered code"]);
}

test("覆盖代码在 sync commit 之后被改 → 报错", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}` })]);
  commitChange(dir);
  const r = run(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}${r.err}`);
  assert.match(r.out, /覆盖文件.*有改动/);
  rmSync(dir, { recursive: true, force: true });
});

test("覆盖代码没动 → 通过", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}` })]);
  const r = run(reg, dir);
  assert.equal(r.code, 0, `期望 exit 0，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /"verdict": "OK"/);
  rmSync(dir, { recursive: true, force: true });
});

test("工作区有未提交的覆盖代码改动 → 报错", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}` })]);
  writeFileSync(join(dir, "sources", "a.ts"), "export const a = 3;\n");
  const r = run(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /未提交/);
  rmSync(dir, { recursive: true, force: true });
});

test("不是 git 仓库 → 明说未核，不静默通过（守住 行 exit 1）", () => {
  const dir = mkdtempSync(join(tmpdir(), "reg-nogit-"));
  mkdirSync(join(dir, "sources"), { recursive: true });
  writeFileSync(join(dir, "sources", "a.ts"), "x\n");
  writeFileSync(join(dir, "sources", "destruct.mjs"), "// x\n");
  const reg = writeRegister(dir, [row({ sync: "基线 abc1234" })]);
  const r = run(reg, dir);
  // 这条测试的名字从第一版起就写着「不静默通过」，但断言一直要求 exit 0——
  // 名字对、断言错。零样本 git 门收紧后，两者才一致。
  assert.equal(r.code, 1, `守住 行零样本未核应 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /git|未核|零样本/);
  rmSync(dir, { recursive: true, force: true });
});

test("零条可核的覆盖文件 → 报零样本", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, covered: "整条付费路径" })]);
  const r = run(reg, dir);
  assert.match(r.out, /零样本|未核/);
  rmSync(dir, { recursive: true, force: true });
});

test("承诺变更证据写了不存在的 commit → 报错", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, promise: "承诺变更证据 deadbeef" })]);
  const r = run(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /承诺变更/);
  rmSync(dir, { recursive: true, force: true });
});

test("覆盖列写「同 P1」时沿引用核，不算零样本", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [
    row({ sync: `基线 ${base}` }),
    row({ sync: `基线 ${base}`, covered: "同 P1" }).replace("| P1 |", "| P2 |"),
  ]);
  commitChange(dir);
  const r = run(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /P2: 覆盖文件.*有改动/);
  assert.doesNotMatch(r.out, /P2: git 门未核/);
  rmSync(dir, { recursive: true, force: true });
});
