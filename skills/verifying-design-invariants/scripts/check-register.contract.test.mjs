// 契约测试：把 SKILL.md「交之前跑机器核对」那张退出码表变成可执行的断言。
//
// 为什么要单独有这个文件：SKILL.md 写着「零样本不算通过」，而脚本在非 git 目录里
// 照样 exit 0 —— 文档与实现之间没有一座会报红的桥。这组测试就是那座桥：
// 改文档或改脚本，只要两边不一致，这里必须红。上一版的两处 P1（19 行被读成 9 行
// 仍判 OK、证据路径怎么改都 OK）都是靠人眼体检发现的，不是靠测试发现的。
//
// 跑：node --test scripts/check-register.contract.test.mjs
//
// 覆盖的文档承诺（SKILL.md 表格逐行对应）：
//   exit 0 = 表读得进来 + 证据指得到东西 + 覆盖文件在 sync commit 之后没动过
//   exit 1 = 状态多值 / 表格中断 / 等级词汇不对 / 编号重复 / 守住缺证据或 commit /
//            未判定没写理由 / 引用的文件不存在 / 代码文件名没有目录前缀 /
//            覆盖文件在 sync commit 之后有改动 / 承诺变更证据指不到东西 /
//            守住 行的 sync commit 零样本未核
//   exit 2 = 文件读不到、找不到表头、表里没有任何可判定的证据引用（零样本）
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync, spawnSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const CHECKER = join(HERE, "check-register.mjs");

const HEAD = [
  "| 编号 | 性质（一句话，可被反例证伪） | owner | 覆盖的文件/函数 | 范围 | 证据等级 | 破坏变体 / 证据命令 | 退出码 | S4 日志 | 状态 | sync commit | 承诺变更证据 |",
  "|---|---|---|---|---|---|---|---|---|---|---|---|",
];

function sh(cwd, args) {
  return execFileSync(args[0], args.slice(1), { cwd, encoding: "utf8" }).trim();
}

// 一个真实 git 仓库：既覆盖代码，也有可核的证据文件（证据路径必须指得到东西）。
function makeRepo() {
  const dir = mkdtempSync(join(tmpdir(), "reg-contract-"));
  sh(dir, ["git", "init", "-q"]);
  sh(dir, ["git", "config", "user.email", "t@example.invalid"]);
  sh(dir, ["git", "config", "user.name", "t"]);
  mkdirSync(join(dir, "sources"), { recursive: true });
  writeFileSync(join(dir, "sources", "a.ts"), "export const a = 1;\n");
  writeFileSync(join(dir, "sources", "destruct.mjs"), "// 破坏变体入口\n");
  writeFileSync(join(dir, "README.md"), "# repo\n");
  sh(dir, ["git", "add", "-A"]);
  sh(dir, ["git", "commit", "-q", "-m", "base"]);
  return { dir, base: sh(dir, ["git", "rev-parse", "HEAD"]) };
}

function row({ sync, covered = "`sources/a.ts:1`", status = "守住", promise = "", evidence = "见 `sources/destruct.mjs:1`",
             level = "L2", s4 = "—" } = {}) {
  return `| P1 | 同一笔钱只扣一次 | me | ${covered} | 单实例 | ${level} | ${evidence} | 0 | ${s4} | ${status} | ${sync} | ${promise} |`;
}

function writeRegister(dir, rows, head = HEAD) {
  const p = join(dir, "invariants", "property-register.md");
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, ["# 登记表", "", ...head, ...rows, ""].join("\n"));
  return p;
}

function run(args) {
  const r = spawnSync("node", [CHECKER, ...args], { encoding: "utf8" });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* 交给断言报空输出 */ }
  return { code: r.status, json, out: r.stdout, err: r.stderr };
}

function runAt(register, root, extra = []) {
  return run([register, "--root", root, ...extra]);
}

// 契约 1：一条「守住」都没核到 sync commit 时，零样本不许读成通过。
test("契约：非 git 目录里 守住 行 → 零样本未核，exit 1（不是静默 OK）", () => {
  const dir = mkdtempSync(join(tmpdir(), "reg-nogit-"));
  mkdirSync(join(dir, "sources"), { recursive: true });
  writeFileSync(join(dir, "sources", "a.ts"), "x\n");
  writeFileSync(join(dir, "sources", "destruct.mjs"), "// x\n");
  const reg = writeRegister(dir, [row({ sync: "基线 abc1234" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /零样本|未核/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 1b：确有环境没有 git 时，必须显式放行——放行是写出来的选择，不是默认行为。
test("契约：--allow-unverified-git 才把零样本降级为通过，且输出仍写明未核", () => {
  const dir = mkdtempSync(join(tmpdir(), "reg-nogit-"));
  mkdirSync(join(dir, "sources"), { recursive: true });
  writeFileSync(join(dir, "sources", "a.ts"), "x\n");
  writeFileSync(join(dir, "sources", "destruct.mjs"), "// x\n");
  const reg = writeRegister(dir, [row({ sync: "基线 abc1234" })]);
  const r = runAt(reg, dir, ["--allow-unverified-git"]);
  assert.equal(r.code, 0, `期望 exit 0，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /未核/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 1c：git 工作区里，覆盖列写成散文（解析不出源码文件）= 同样零样本。
test("契约：git 工作区里覆盖列解析不出源码文件 → 守住 行 exit 1", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, covered: "整条付费路径" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /零样本|未核|源码文件/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 2：证据路径没有目录前缀也必须核存在性（旧版只认带斜杠的路径，
// 于是 `ghost.md` 这种「根本不存在」的证据照样 exit 0）。
test("契约：证据写 ghost.md（无目录前缀且不存在）→ exit 1", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, evidence: "见 ghost.md 第 3 节" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /ghost\.md/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 2b：反过来，根目录真实存在的文件不许被当成「指不到东西」误报。
test("契约：承诺变更证据指向根目录 README.md（存在）→ exit 0", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, promise: "README.md" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 0, `期望 exit 0，得到 ${r.code}；输出 ${r.out}`);
  assert.doesNotMatch(r.out, /既不是 commit 也指不到文件/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 3：输入集为空 = 未校验。空模板（全是 未判定 占位行、没有任何证据引用）
// 不许报 OK —— 那正是「断链 0 条、exit 0」的同款假通过。
test("契约：没有任何可判定的证据引用 → exit 2 未判定，并打印候选数 0", () => {
  const dir = mkdtempSync(join(tmpdir(), "reg-empty-"));
  const reg = writeRegister(dir, [
    "| P1 |  |  |  |  |  |  |  |  | 未判定 |  |  |",
    "| P2 |  |  |  |  |  |  |  |  | 未判定 |  |  |",
  ]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 2, `期望 exit 2，得到 ${r.code}；输出 ${r.out}`);
  assert.ok(r.json, `输出不是 JSON：${r.out}${r.err}`);
  assert.equal(r.json.evidence_candidates, 0, "必须打印证据候选数，0 就是未校验");
  rmSync(dir, { recursive: true, force: true });
});

// 契约 4：用法里的参数顺序不许改变结论（--root 写在文件前后都应等价）。
test("契约：--root 在文件前与在文件后等价", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}` })]);
  const before = run(["--root", dir, reg]);
  const after = run([reg, "--root", dir]);
  assert.equal(after.code, 0, `文件在前应 exit 0，得到 ${after.code}；输出 ${after.out}`);
  assert.equal(before.code, after.code, `顺序不同结论不同：${before.code} vs ${after.code}；输出 ${before.out}`);
  assert.equal(before.json?.verdict, after.json?.verdict);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 5：空行截断的第二张表 = 表格中断（19 行被读成 9 行却判 OK 的那次事故）。
test("契约：表格中间出现空行再接表行 → exit 1，并说清从第几行起", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [
    row({ sync: `基线 ${base}` }),
    "",
    row({ sync: `基线 ${base}` }).replace("| P1 |", "| P2 |"),
  ]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /中断/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 6：读不进来 = 未判定，不是失败也不是通过。
test("契约：找不到表头 → exit 2", () => {
  const dir = mkdtempSync(join(tmpdir(), "reg-nohead-"));
  const p = join(dir, "property-register.md");
  writeFileSync(p, "# 只有散文，没有表格\n");
  const r = runAt(p, dir);
  assert.equal(r.code, 2, `期望 exit 2，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /表头/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 7：列数不齐 = 表被改坏，不是「随便读读」。
test("契约：某行列数与表头不一致 → exit 1", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}` }).replace(/\|[^|]*$/, "")]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /列数/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 8：覆盖列里写的源码路径不存在 = 这条「守住」覆盖的是一份不存在的代码。
// （收紧证据列时曾把这一腿一起关掉：真实表上 32 条硬告警掉到 4 条，没有任何测试喊。）
test("契约：覆盖的文件/函数 列引用的源码不存在 → exit 1", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, covered: "`sources/gone.ts:1`" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /gone\.ts/);
  rmSync(dir, { recursive: true, force: true });
});

// 契约 9：未判定 行里还没落地的命令不算「引用的文件不存在」（它不是漏，是还没跑到）。
test("契约：未判定 行的证据命令写了不存在的文件 → 不报硬告警", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [
    row({ sync: `基线 ${base}`, status: "未判定", evidence: "将来跑 node pending-only.mjs（还没写）" }),
  ]);
  const r = runAt(reg, dir);
  assert.doesNotMatch(r.out, /pending-only\.mjs/);
  rmSync(dir, { recursive: true, force: true });
});

// ---- 以下是 references/pilot-findings.md 里那些「摩擦 → 结构」的机器判据。
// 结构当时都在，但没有一条测试锁它们：改一次核对器就可能静默丢掉，而测试全绿。
// 每条都按试点原文的症状造夹具，测的是「这个症状今天还会不会被抓住」。

// 摩擦 1（试点原文）：状态列被写成「守住（单写者）；双写者报红=known limit」，机器读不出单值。
test("摩擦1：状态不是单值 → exit 1；括号里写范围是合法写法，不许误杀", () => {
  const { dir, base } = makeRepo();
  const bad = writeRegister(dir, [row({ sync: `基线 ${base}`, status: "守住（单写者）；双写者报红=known limit" })]);
  const r1 = runAt(bad, dir);
  assert.equal(r1.code, 1, `多值状态应 exit 1，得到 ${r1.code}；输出 ${r1.out}`);
  assert.match(r1.out, /状态不是单值/);

  const ok = writeRegister(dir, [row({ sync: `基线 ${base}`, status: "守住（单写者）" })]);
  const r2 = runAt(ok, dir);
  assert.equal(r2.code, 0, `带范围括号的 守住 应 exit 0，得到 ${r2.code}；输出 ${r2.out}`);
  rmSync(dir, { recursive: true, force: true });
});

// 摩擦 5（试点原文）：两个人报同一模型状态数 16 vs 39，差点被判矛盾；
// 结论是「会随输入增长的数字不能当守住证据」，只能记成观察。
test("摩擦5：守住 行挂会漂的数字 → WARN；--strict 下 exit 1；标了观察值则放行", () => {
  const { dir, base } = makeRepo();
  const drift = writeRegister(dir, [row({ sync: `基线 ${base}`, evidence: "S4 exit 0 / FAIL=0 / 1,718 步" })]);
  const r1 = runAt(drift, dir);
  assert.equal(r1.code, 0, `默认只 WARN，得到 ${r1.code}；输出 ${r1.out}`);
  assert.match(r1.out, /随输入增长的数字/);
  const r2 = runAt(drift, dir, ["--strict"]);
  assert.equal(r2.code, 1, `--strict 应 exit 1，得到 ${r2.code}`);

  const observed = writeRegister(dir, [row({ sync: `基线 ${base}`, evidence: "S4 exit 0 / 1,718 步（观察值，非不变量）" })]);
  const r3 = runAt(observed, dir);
  assert.doesNotMatch(r3.out, /随输入增长的数字/);
  rmSync(dir, { recursive: true, force: true });
});

// 摩擦 8（试点原文）：六行「未判定」被读成「全线失败」；结构是加证据等级，
// 且 L3 的定义是 L2 + 真实日志——写了 L3 却拿不出 S4 的 PASS 必须报错。
test("摩擦8：证据等级写 L3 但 S4 没有 PASS → exit 1；补上 PASS 后放行", () => {
  const { dir, base } = makeRepo();
  const bad = writeRegister(dir, [row({ sync: `基线 ${base}`, s4: "日志粒度不足", level: "L3" })]);
  const r1 = runAt(bad, dir);
  assert.equal(r1.code, 1, `L3 缺 S4 PASS 应 exit 1，得到 ${r1.code}；输出 ${r1.out}`);
  assert.match(r1.out, /L3/);

  const ok = writeRegister(dir, [row({ sync: `基线 ${base}`, s4: "PASS", level: "L3" })]);
  const r2 = runAt(ok, dir);
  assert.equal(r2.code, 0, `L3 + S4 PASS 应 exit 0，得到 ${r2.code}；输出 ${r2.out}`);
  rmSync(dir, { recursive: true, force: true });
});

// 摩擦 3（试点原文）：脚本把「找错目录」报成 UNDECIDED——自由文本的等级词汇同理，
// 写成「TLA+/TLC 建模」会让等级那道门整列失效。
test("等级词汇写成自由文本 → exit 1，并说清只允许 L1/L2/L3", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, level: "TLA+/TLC 建模" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /证据等级只允许/);
  rmSync(dir, { recursive: true, force: true });
});

// 摩擦 6（试点原文）：一个人 write 前没读，把别人的记录覆盖掉；
// 落到机器上就是同一张表里编号重复——不报就等于默许两条性质抢同一个编号。
test("编号重复 → exit 1", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}` }), row({ sync: `基线 ${base}` })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /编号重复/);
  rmSync(dir, { recursive: true, force: true });
});

// 「未判定」必须带理由：缺什么/谁没签。写「等技术方案」不算没写下文，
// 但写「等后续安排」这种既不含缺也不含未/无的句子，等于没写。
test("未判定 没写理由 → exit 1", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, status: "未判定", evidence: "等后续安排" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /没写理由/);
  rmSync(dir, { recursive: true, force: true });
});

// 摩擦 7 的延伸：证据只留一个 URL，等于把可核性交给外部站点（会 404、会改）。
test("证据写成 URL → exit 1（无法核对存在性）", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, evidence: "见 https://example.invalid/run/42" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /URL/);
  rmSync(dir, { recursive: true, force: true });
});

// 第三轮（试点原文）：有人把 `ds-bot/src/host/ledger.js:133` 改成 `ledger.js:133`
// 来消掉告警，证据反而不可核。带行号却没有目录前缀必须报。
test("带行号的代码文件名没有目录前缀 → exit 1", () => {
  const { dir, base } = makeRepo();
  const reg = writeRegister(dir, [row({ sync: `基线 ${base}`, evidence: "改 ledger.js:133 的边界" })]);
  const r = runAt(reg, dir);
  assert.equal(r.code, 1, `期望 exit 1，得到 ${r.code}；输出 ${r.out}`);
  assert.match(r.out, /没有目录前缀/);
  rmSync(dir, { recursive: true, force: true });
});
