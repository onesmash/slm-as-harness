#!/usr/bin/env node
// 性质登记表的机器核对器：把「逐行核对」从人眼变成退出码。
//
// 用法：node check-register.mjs <property-register.md> [--root DIR] [--strict]
//   --root    解析表内证据路径的基准目录（默认登记表所在目录）
//   --strict  把「风格类」WARN 也当失败（默认只提示）
//
// 退出码：0 = 没有 ERROR 且没有硬告警；1 = 至少一个 ERROR 或硬告警（含表格中断）；2 = 文件读不到或没有表格
//
// 它检查两件事：① 登记表能不能被机器读（单值状态、列数、等级词汇、一张表不中断）；
// ② 证据指得到东西（引用的文件在不在、有没有目录前缀）。**它不执行任何命令**——
// 「退出码 0」是自述，不是它跑出来的。性质对不对只能靠破坏变体与反例，静态检查替代不了。
//
// 硬告警（默认就算失败）：引用的文件不存在、引用是 URL、代码文件名没有目录前缀。
// 这三类都会让下一个人「按表去翻却扑空」。
//
// 第三件事（漂移门）：拿「覆盖的文件」与 sync commit 对 git 事实核一遍——
// 覆盖文件在 sync commit 之后被改过（已提交或未提交），这条「守住」描述的就是过去。
// 它只读 git，不执行验证命令；git 不可用时明说「未核」，不许静默当通过。

import { readFileSync, existsSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { execFileSync } from "node:child_process";

const OK = 0;
const BAD = 1;
const UNUSABLE = 2;

const STATES = new Set(["守住", "报红", "未判定"]);
// 未判定必须给出理由——「缺什么」或「谁没签」，不许空着
const UNDECIDED_REASON = /(缺|未|无|不适|not|UNDECIDED|待签|不建模)/i;
// 守住必须能指到一次真实的运行。
// 别用 \b0\b 这种宽判据：散文里的「0 条」「60 行」会让它假通过。
// commit 必须含至少一个 a-f 字母：纯数字（seed、计数）不是 commit
const COMMIT = /\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b/i;
// 带行号的代码文件名（要求带 :行号，避免把 cfg/json 之类目录内文件也算进来）
const BARE_CODE = /(?:^|[\s(（`])([\w-]+\.(?:mjs|js|ts|py|go|rs|java):\d+(?:-\d+)?)/g;
// 会随输入增长的量
const DRIFT = /(\d[\d,]*\s*(步|行|条|字节)|步数|行数|条数)/;
// 明示为观察值
const OBSERVED = /(观察值|观察|snapshot|快照|随日志增长|非不变量)/i;
const PATH_LIKE = /(?:^|[\s(（`])((?:[\w.-]+\/)+[\w.-]+\.(?:jsonl|json|mjs|md|tla|cfg|sh|js|ts))/g;
// 「覆盖的文件/函数」里的源码路径：允许不带目录前缀（`store.ts:557` 也是有效指认），
// 行号后缀在匹配时自然被丢掉。
const COVERED_FILE = /([A-Za-z0-9_.-]+(?:\/[A-Za-z0-9_.-]+)*\.(?:mjs|cjs|js|ts|tsx|jsx|py|go|rs|java|kt|swift|rb|php|sql|vue|svelte))/g;
// 「承诺变更证据」为空时的合法写法
const EMPTY_CELL = /^(—+|-+|n\/a|不适用|无)$/i;

let REPO_ROOT = null; // main 里解析，checkRow 只读

function gitAt(cwd, args) {
  return execFileSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
}

function tryGit(cwd, args) {
  try { return { ok: true, out: gitAt(cwd, args) }; } catch (e) { return { ok: false, err: e.message }; }
}

function coveredFiles(text) {
  const out = new Set();
  for (const m of text.matchAll(COVERED_FILE)) out.add(m[1]);
  return [...out];
}

// 「覆盖同 P1」是合法写法：跟着引用走，别逼人把同一串文件抄两遍（抄两遍就会有一遍过期）。
// 深度上限防环：P1 同 P2、P2 同 P1 时必须停下来报零样本，而不是栈溢出。
const SAME_AS = /同\s*(P[0-9]+)/i;

function filesForRow(row, header, byId, depth = 0) {
  const i = column(header, "覆盖的文件/函数");
  const text = i >= 0 ? row.cells[i] : "";
  const own = coveredFiles(text);
  if (own.length > 0) return own;
  const m = text.match(SAME_AS);
  if (!m || depth >= 3) return [];
  const ref = byId.get(m[1]);
  if (!ref) return [];
  return filesForRow(ref, header, byId, depth + 1);
}

// 一行的漂移判定：sync commit 之后覆盖文件动过没有。
// checked=false 的行必须被「零样本」统计看见，否则整张表会在没有 git 的机器上静默通过。
function driftCheck(row, header, files) {
  const errors = [];
  const warns = [];
  const cell = (name) => {
    const i = column(header, name);
    return i >= 0 ? row.cells[i] : "";
  };
  const id = row.cells[0] || `(第 ${row.line} 行)`;
  const commitText = cell("commit") || cell("sync");
  if (/pending/i.test(commitText)) return { checked: false, errors, warns, reason: "pending" };
  const sha = (commitText.match(COMMIT) || [])[0];
  if (!sha) return { checked: false, errors, warns: [`${id}: git 门未核（sync commit 列没有可解析的 commit）`], reason: "no-commit" };
  if (files.length === 0) return { checked: false, errors, warns: [`${id}: git 门未核（覆盖列没有可解析的源码文件，零样本不算通过）`], reason: "no-files" };
  if (!REPO_ROOT) return { checked: false, errors, warns: [`${id}: git 门未核（不在 git 工作区里）`], reason: "no-repo" };

  const rev = tryGit(REPO_ROOT, ["rev-parse", "--verify", "--quiet", `${sha}^{commit}`]);
  if (!rev.ok) return { checked: false, errors: [`${id}: sync commit 在仓库里不存在 -> ${sha}`], warns, reason: "bad-commit" };

  const diff = tryGit(REPO_ROOT, ["diff", "--name-only", `${sha}`, "HEAD", "--", ...files]);
  if (!diff.ok) {
    warns.push(`${id}: git 门核不动（git diff 失败：${diff.err.slice(0, 80)}）`);
    return { checked: false, errors, warns, reason: "diff-failed" };
  }
  const committed = diff.out.split("\n").map((s) => s.trim()).filter(Boolean);
  if (committed.length > 0) {
    errors.push(`${id}: 覆盖文件在 sync commit（${sha}）之后有改动 -> ${committed.slice(0, 4).join(", ")}${committed.length > 4 ? ` 等 ${committed.length} 个` : ""}；先按 S5 维护流程处理，再前移 sync commit`)
  }

  const dirty = tryGit(REPO_ROOT, ["status", "--porcelain", "--", ...files]);
  if (dirty.ok) {
    const lines = dirty.out.split("\n").map((s) => s.trim()).filter(Boolean);
    if (lines.length > 0) errors.push(`${id}: 覆盖文件有未提交改动（未提交也算漂移）-> ${lines.slice(0, 4).join(", ")}`);
  } else {
    warns.push(`${id}: git status 核不动，未提交改动未核`);
  }
  return { checked: true, errors, warns, reason: null };
}

// 「承诺变更证据」：性质有意改动时，必须指得到一次提交或一份可打开的文件。
function promiseEvidenceCheck(row, header, root) {
  const errors = [];
  const i = column(header, "承诺变更证据");
  if (i < 0) return errors;
  const raw = (row.cells[i] || "").trim();
  if (!raw || EMPTY_CELL.test(raw)) return errors;
  const id = row.cells[0] || `(第 ${row.line} 行)`;
  const sha = (raw.match(COMMIT) || [])[0];
  if (sha) {
    if (REPO_ROOT) {
      const rev = tryGit(REPO_ROOT, ["rev-parse", "--verify", "--quiet", `${sha}^{commit}`]);
      if (!rev.ok) errors.push(`${id}: 承诺变更证据里的 commit 不存在 -> ${sha}`);
    }
    return errors;
  }
  const paths = raw.match(/(?:[\w.-]+\/)+[\w.-]+\.[a-z0-9]{1,6}/gi) || [];
  if (paths.length === 0) {
    errors.push(`${id}: 承诺变更证据既不是 commit 也指不到文件（读到「${raw.slice(0, 40)}」）`);
  } else if (!paths.some((p) => existsSync(resolve(root, p)))) {
    errors.push(`${id}: 承诺变更证据指不到文件 -> ${paths[0]}`);
  }
  return errors;
}

function clean(cell = "") {
  return cell.replace(/[`*]/g, "").replace(/\s+/g, " ").trim();
}

function splitRow(line) {
  // 去掉首尾竖线后按 | 切；表格里不出现转义竖线
  return line.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map(clean);
}

function readTable(text) {
  const lines = text.split("\n");
  const headIndex = lines.findIndex((l) => l.trim().startsWith("|") && l.includes("编号"));
  if (headIndex < 0) return { error: "找不到表头：需要一行以 | 开头且含「编号」" };
  const header = splitRow(lines[headIndex]);
  const rows = [];
  const tail = [];
  let ended = false;
  for (let i = headIndex + 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim().startsWith("|")) {
      // 空行/散文：第一张表到此结束。但继续往下扫——表行若在空行之后又出现，
      // 说明表被截断（或有人加了第二张表），两种情况都不许静默放行。
      if (rows.length > 0) ended = true;
      continue;
    }
    if (ended) {
      tail.push({ line: i + 1 });
      continue;
    }
    if (/^\s*\|[\s:|-]+\|\s*$/.test(line)) continue; // 分隔行
    rows.push({ line: i + 1, cells: splitRow(line) });
  }
  return { header, rows, tail };
}

function column(header, ...names) {
  for (const name of names) {
    const exact = header.findIndex((h) => h === name);
    if (exact >= 0) return exact;
  }
  for (const name of names) {
    const partial = header.findIndex((h) => h.includes(name));
    if (partial >= 0) return partial;
  }
  return -1;
}

function checkRow(header, row, root) {
  const errors = [];
  const warns = [];
  const hardWarns = [];
  const id = row.cells[0] || `(第 ${row.line} 行)`;
  if (row.cells.length !== header.length) {
    errors.push(`${id}: 列数 ${row.cells.length} != 表头 ${header.length}`);
    return { errors, warns, hardWarns };
  }

  const statusAt = column(header, "状态");
  const status = statusAt >= 0 ? row.cells[statusAt] : "";
  // 判据一律排除状态列：否则「未判定」三个字里的「未」会永远满足「写了理由」
  const withoutStatus = row.cells.filter((_, i) => i !== statusAt).join(" ");
  const rowText = row.cells.join(" ");
  if (!withoutStatus.trim()) errors.push(`${id}: 整行几乎没有内容`);
  // 占位行：除编号与状态外没填实质内容（等级不算内容）
  const filled = row.cells
    .filter((_, i) => i !== statusAt && i !== 0)
    .join("")
    .replace(/L[123]/gi, "")
    .trim();
  const isPlaceholder = filled === "";

  const m = status.match(/^(守住|报红|未判定)\s*[（(]([^）)]*)[）)]?$/);
  const bare = m ? m[1] : status;
  if (!STATES.has(bare)) errors.push(`${id}: 状态不是单值（读到「${status.slice(0, 60)}」）`);
  if (m && m[2] !== undefined && m[2].length > 30) {
    warns.push(`${id}: 状态括号里的范围太长，建议移到「范围」列`);
  }

  const cell = (name) => {
    const i = column(header, name);
    return i >= 0 ? row.cells[i] : "";
  };
  const has = (name) => column(header, name) >= 0;

  // 证据等级的词汇必须封闭：L1/L2/L3，或不建模（必须写清谁覆盖）。
  // 自由文本（例如「TLA+/TLC 建模」）会让等级轴整列失效——L3 那道门永远不触发。
  if (has("证据等级")) {
    const g = cell("证据等级").trim();
    if (g && /^不建模/.test(g)) {
      if (!/(由|用|归)[^。；]*?(覆盖|守|负责)/.test(g)) {
        (isPlaceholder ? warns : errors).push(`${id}: 不建模 但没写谁覆盖（写成「不建模：<理由>；由<谁>覆盖」）`);
      }
    } else if (g && !/^L[123]\b/.test(g)) {
      (isPlaceholder ? warns : errors).push(`${id}: 证据等级只允许 L1/L2/L3 或「不建模：…；由…覆盖」，读到「${g.slice(0, 40)}」`);
    }
  }

  // L3 的定义是「L2 + 真实日志」：任何状态写了 L3，都必须有 S4 的 PASS
  if (/L3/i.test(cell("证据等级"))) {
    const why = !has("S4")
      ? "表头没有「S4 日志」列，无法支撑 L3（L3 = L2 + 真实日志）"
      : !/\bPASS\b/i.test(cell("S4"))
        ? "S4 列没有 PASS（L3 = L2 + 真实日志）"
        : null;
    if (why) (isPlaceholder ? warns : errors).push(`${id}: 证据等级写 L3，但 ${why}`);
  }

  if (bare === "守住") {
    // ① 只回答一个问题：有没有记录下「跑绿过」。它故意宽松（`exit 0` 即可）；
    //    真正拦住假守住的是破坏变体、L3/S4、pending 与观察值四道。
    const exitCell = cell("退出码");
    const evidence = exitCell || withoutStatus;
    if (!/\b0\b|\bPASS\b/i.test(evidence)) {
      errors.push(`${id}: 守住 但证据里没有 0/PASS（exit 1 是报红、exit 2 是未判定，都不能算守住）`);
    }
    // ② 破坏变体：没有见过失败的性质不许记守住
    if (has("破坏变体")) {
      const dv = cell("破坏变体").trim();
      if (dv === "" || /^(无|n\/a|—|-|不适用)$/i.test(dv)) {
        errors.push(`${id}: 守住 但破坏变体列为空（没见过的失败不算验证）`);
      }
    }
    // ③ sync commit：pending 表示代码变了没重跑，只能记未判定
    const commitCell = cell("commit") || cell("sync");
    if (/pending/i.test(commitCell)) {
      errors.push(`${id}: 守住 但 sync commit 是 pending（代码变了没重跑，只能记未判定）`);
    } else if (!COMMIT.test(commitCell)) {
      errors.push(`${id}: 守住 但 sync commit 列没有 commit`);
    }
    if (!m) warns.push(`${id}: 守住 没写适用范围（建议 守住（单写者）这类）`);
    // ⑤ 会漂的数字不能当承诺
    if (DRIFT.test(withoutStatus) && !OBSERVED.test(withoutStatus)) {
      warns.push(`${id}: 守住 里挂了会随输入增长的数字（步数/行数/条数），请标为观察值或去掉`);
    }
  }

  if (bare === "未判定" && !UNDECIDED_REASON.test(withoutStatus)) {
    if (isPlaceholder) warns.push(`${id}: 占位行还没填（性质/证据/理由都空）`);
    else errors.push(`${id}: 未判定 但没写理由（缺什么/谁没签）`);
  }

  if (/https?:\/\//.test(rowText)) {
    hardWarns.push(`${id}: 引用里有 URL，无法核对存在性（证据请写仓库相对路径）`);
  }

  // 带行号的代码文件名却没有目录前缀：证据没法核对。
  // 试点里有人把 ds-bot/src/host/ledger.js 改成 ledger.js 来消掉警告，证据质量反而下降。
  for (const bm of withoutStatus.matchAll(BARE_CODE)) {
    const base = bm[1];
    if (withoutStatus.includes(`/${base}`)) continue;
    hardWarns.push(`${id}: ${base} 没有目录前缀，无法核对存在性（写成 repo 相对路径）`);
  }

  // 注意：带 g 的 match() 返回整段匹配（含前缀空格/反引号），不是捕获组——必须用 matchAll
  for (const pm of withoutStatus.matchAll(PATH_LIKE)) {
    const path = pm[1];
    if (!existsSync(resolve(root, path))) hardWarns.push(`${id}: 引用的文件不存在 -> ${path}`);
  }
  return { errors, warns, hardWarns };
}

function main(argv) {
  const file = argv.find((a) => !a.startsWith("--"));
  if (!file) {
    console.error("用法：node check-register.mjs <property-register.md> [--root DIR] [--strict]");
    return UNUSABLE;
  }
  let text;
  try {
    text = readFileSync(file, "utf8");
  } catch (e) {
    console.log(JSON.stringify({ error: `读不到 ${file}: ${e.message}` }, null, 2));
    return UNUSABLE;
  }
  const table = readTable(text);
  if (table.error) {
    console.log(JSON.stringify({ error: table.error }, null, 2));
    return UNUSABLE;
  }
  const rootFlag = argv.indexOf("--root");
  const root = rootFlag >= 0 ? resolve(argv[rootFlag + 1]) : dirname(resolve(file));
  const strict = argv.includes("--strict");

  // git 门：只在「登记表所在目录在某个工作区里」时可用；不可用必须说出来（零样本不等于通过）。
  const top = tryGit(root, ["rev-parse", "--show-toplevel"]);
  REPO_ROOT = top.ok ? top.out : null;

  const errors = [];
  const warns = [];
  const hardWarns = [];
  const seen = new Set();
  const skipped = [];
  const byId = new Map(table.rows.map((r) => [(r.cells[0] || "").trim(), r]));
  let gitChecked = 0;
  if (!REPO_ROOT) warns.push(`git 门未核：${root} 不在 git 工作区里（或没装 git），sync commit 是否过期无法判定`);
  for (const row of table.rows) {
    const id = (row.cells[0] || "").trim();
    if (id && seen.has(id)) errors.push(`${id}: 编号重复`);
    seen.add(id);
    const r = checkRow(table.header, row, root);
    errors.push(...r.errors);
    warns.push(...r.warns);
    hardWarns.push(...r.hardWarns);
    errors.push(...promiseEvidenceCheck(row, table.header, root));
    const d = driftCheck(row, table.header, filesForRow(row, table.header, byId));
    errors.push(...d.errors);
    warns.push(...d.warns);
    if (d.checked) gitChecked++;
    else skipped.push({ id: id || `第 ${row.line} 行`, reason: d.reason });
  }
  if (table.rows.length > 0 && gitChecked === 0 && REPO_ROOT) {
    warns.push(`git 门零样本：${table.rows.length} 行里一条都没核到（没有可解析的覆盖文件、sync commit 写不出，或全标了 pending）`);
  }
  if (table.rows.length === 0) errors.push("表格没有数据行");
  // 表格中间中断：读了一半不等于读了。上一次是 19 行被读成 9 行，仍然 verdict=OK。
  if (table.tail.length > 0) {
    const last = table.rows.length > 0 ? table.rows[table.rows.length - 1].line : "表头";
    errors.push(`表格在第 ${last} 行之后中断：第 ${table.tail[0].line} 行起还有 ${table.tail.length} 行以 | 开头。登记表只允许一张表；若是第二张表，请并进主表`);
  }

  const hasRange = column(table.header, "范围") >= 0;
  const hasExit = column(table.header, "退出码") >= 0;
  const hasLevel = column(table.header, "证据等级") >= 0;
  if (!hasRange) warns.push("表头缺「范围」列：守住 的适用范围无处可写");
  if (!hasExit) warns.push("表头缺「退出码」列：退出码只剩自由文本，机器读不了");
  if (!hasLevel) warns.push("表头缺「证据等级」列：读者分不清这条守住覆盖到 L1/L2/L3 哪一层");

  // 硬告警默认算失败：证据指不到东西时，「表能读」不是通过。
  const failed = errors.length > 0 || hardWarns.length > 0 || (strict && warns.length > 0);
  const stat = statSync(file);
  console.log(JSON.stringify({
    file,
    mtime: stat.mtime.toISOString(),
    columns: table.header,
    rows: table.rows.length,
    verdict: failed ? "FAIL" : "OK",
    git_check: { repo: REPO_ROOT, checked: gitChecked, skipped },
    errors,
    hard_warnings: hardWarns,
    warnings: warns,
  }, null, 2));
  return failed ? BAD : OK;
}

process.exit(main(process.argv.slice(2)));
