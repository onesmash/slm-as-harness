#!/usr/bin/env node
// 技能内交叉引用的机器核对器：把「链接没断」从人眼变成退出码。
//
// 用法：node check-paths.mjs [SKILL_ROOT]
//   默认 SKILL_ROOT = 本脚本所在目录的上一级。
//
// 退出码：0 = 有候选且全部解析得到；1 = 至少一个引用指不到文件、或「见下「…」」指向的
//        小标题不存在；2 = 候选数为 0（未校验——不是通过）
//
// 为什么 2 和 0 要分开：
//   上一版我用一次性命令数 markdown 链接 `[文字](路径)`，这个技能里那种链接是
//   0 条，于是「断链 0、exit 0」看起来通过了，其实什么也没检查。
//   输入集为空的检查必然通过，它不能当证据。所以候选数为 0 一律报「未校验」。
//
// 它只查技能自有目录（references/ templates/ scripts/ examples/）下的反引号路径。
// 别的反引号内容（仓库简写 `cursor/plugins`、产出目录 `out/`、命令 `PATH=...`）
// 不在本文件的可判定范围内，硬判会产生一堆假警报。

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { dirname, resolve, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const OK = 0;
const BAD = 1;
const UNVERIFIED = 2;

// 技能自有目录：只有这些前缀的引用，其存在性是可判定的
const OWN = /^(references|templates|scripts|examples)\/\S*$/;
// 反引号里的一行
const TICK = /`([^`\n]+)`/g;
// 「见下「六条判据」」这类指路：引号里是标题，不是路径，上一版检查器看不见它。
// 改标题名（四项 → 六条）之后旧指路会悬空，而路径检查仍然 exit 0。
const SEE_BELOW = /见下[「`]([^」`\n]+)[」`]/g;
const HEADING = /^#{1,6}\s+(.+)$/gm;
// 这个技能里「**可重跑的六条判据**（全文见…）」是加粗段、不是 # 标题，也要能当锚点
const BOLD_LINE = /^\*\*([^*\n]+)\*\*/gm;
const SKIP_DIRS = new Set([".git", "node_modules", "out", "outbug", "states"]);

function walkMarkdown(root, out = []) {
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.name.startsWith(".")) continue;
    const full = join(root, entry.name);
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) continue;
      walkMarkdown(full, out);
    } else if (entry.name.endsWith(".md")) {
      out.push(full);
    }
  }
  return out;
}

// 反向检查：references/ 与 templates/ 下的每份文件都必须被至少一份 md 引用，
// 否则它是一份「没人能走到」的文档——SKILL.md 的细节清单就是它的入口。
// 只查这两个目录：scripts/ 与 examples/ 里的文件由命令按路径调用，不必被散文点名。
function documents(root) {
  const out = [];
  for (const dir of ["references", "templates"]) {
    const full = join(root, dir);
    if (!existsSync(full)) continue;
    for (const entry of readdirSync(full, { withFileTypes: true })) {
      if (entry.isDirectory() || entry.name.startsWith(".")) continue;
      out.push(`${dir}/${entry.name}`);
    }
  }
  return out.sort();
}

function main(argv) {
  const here = dirname(fileURLToPath(import.meta.url));
  const root = resolve(argv.find((a) => !a.startsWith("--")) ?? join(here, ".."));
  if (!existsSync(root)) {
    console.log(JSON.stringify({ error: `技能目录不存在：${root}` }, null, 2));
    return UNVERIFIED;
  }

  const occurrences = [];
  for (const file of walkMarkdown(root)) {
    const text = readFileSync(file, "utf8");
    for (const match of text.matchAll(TICK)) {
      const ref = match[1].trim();
      if (!OWN.test(ref)) continue;
      occurrences.push({ file: relative(root, file), ref });
    }
  }

  // 指路检查：见下「X」→ 本文档里必须有一个标题包含 X
  const brokenAnchors = [];
  let anchorsChecked = 0;
  for (const file of walkMarkdown(root)) {
    const text = readFileSync(file, "utf8");
    const headings = [
      ...[...text.matchAll(HEADING)].map((m) => m[1].trim()),
      ...[...text.matchAll(BOLD_LINE)].map((m) => m[1].trim()),
    ];
    for (const match of text.matchAll(SEE_BELOW)) {
      anchorsChecked += 1;
      const phrase = match[1].trim();
      if (!headings.some((h) => h.includes(phrase))) {
        const line = text.slice(0, match.index).split("\n").length;
        brokenAnchors.push({ file: relative(root, file), line, phrase });
      }
    }
  }

  const missing = [];
  const refs = [...new Set(occurrences.map((o) => o.ref))].sort();
  for (const ref of refs) {
    if (!existsSync(resolve(root, ref))) {
      const from = [...new Set(occurrences.filter((o) => o.ref === ref).map((o) => o.file))];
      missing.push({ ref, referencedIn: from });
    }
  }

  // 候选数为 0：说明这个文件里没有可判定的引用，检查没跑过任何东西
  if (refs.length === 0) {
    console.log(JSON.stringify({
      root,
      verdict: "UNVERIFIED",
      candidates: 0,
      reason: "没有找到任何技能自有目录下的反引号路径：本次校验的输入集为空，结论只能是未校验",
    }, null, 2));
    return UNVERIFIED;
  }

  // 反向：没人引用的文档等于不存在
  const orphans = documents(root).filter((doc) => !refs.includes(doc));

  const verdict = missing.length > 0 || orphans.length > 0 || brokenAnchors.length > 0 ? "FAIL" : "OK";
  console.log(JSON.stringify({
    root,
    verdict,
    // 先报输入集，再报结论：零样本不许读成通过
    candidates: refs.length,
    occurrences: occurrences.length,
    files: new Set(occurrences.map((o) => o.file)).size,
    documentsChecked: documents(root).length,
    anchorsChecked,
    anchors: anchorsChecked === 0 ? "UNCHECKED：没有「见下「…」」候选，指路检查未校验" : "OK",
    missing,
    orphans,
    brokenAnchors,
  }, null, 2));
  return verdict === "OK" ? OK : BAD;
}

process.exit(main(process.argv.slice(2)));
