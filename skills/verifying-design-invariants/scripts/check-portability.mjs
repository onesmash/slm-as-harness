#!/usr/bin/env node
// 可移植性核对器：把「这份文档有没有写死某台机器的信息」变成退出码。
//
// 用法：node check-portability.mjs [SKILL_ROOT] [--strict]
//   默认 SKILL_ROOT = 本脚本所在目录的上一级。
//   --strict  把 WARN 也当失败。
//
// 退出码：0 = 无误报级问题；1 = 至少一个 ERROR（或 --strict 下有 WARN）；
//        2 = 没扫到任何文档（未校验，不是通过）
//
// 为什么不能只用 grep '/Users/'：
//   用户名的绝对路径只是「本机信息」的一种形状。真正会跟着人跑掉的信息有四类：
//   U 身份路径   /Users/<名字>、/home/<名字>、C:\Users\<名字>      —— 任何地方都是 ERROR
//   H 家目录假设  ~/... 或 $HOME/... 出现在**可执行命令**里            —— ERROR
//   A 宿主绝对路径 /usr/... /opt/... /Library/... 出现在可执行命令里  —— ERROR
//   P 散文里的本机事实  出现在没有「本机/快照」标记的段落里           —— WARN
//
// 唯一豁免：`${VAR:-默认值}` 里的默认值。默认值本来就是「本机取值，可被覆盖」，
// 那是这台机器的合法位置；把它写进命令正文（而不是变量默认值）才是把机器带进文档。

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, resolve, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const OK = 0;
const BAD = 1;
const UNVERIFIED = 2;

// U：身份路径。任何位置都不允许——换个人、换台机器就失效，且泄露用户名。
const IDENTITY = /(?:\/Users|\/home)\/[A-Za-z0-9._-]+|\/root\b|C:\\+Users\\+[A-Za-z0-9._-]+/g;
// H/A：家目录与宿主绝对路径。命令里出现就是写死；散文里出现则要求本机标记。
const HOSTY = /(?:~|\$HOME)\/[^\s'"`()（）]+|\/(?:usr|opt|Library|etc|var|private|bin|sbin)\/[^\s'"`()（）]+/g;
// 变量默认值：${X:-...} / ${X-...}，豁免区间（长度保持不变，避免位置错位）
const DEFAULT_SPAN = /\$\{[^}]*:-[^}]*\}/g;
// 段落标记：这些词说明作者在讲「本台机器」，允许出现本机事实
const MARKED = /(本机|快照|这台机器|已实测|实测于)/;

function maskDefaults(line) {
  return line.replace(DEFAULT_SPAN, (m) => " ".repeat(m.length));
}

function scan(root) {
  const docs = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (entry.name.startsWith(".")) continue;
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        if (["node_modules", "states", "out", "outbug"].includes(entry.name)) continue;
        walk(full);
      } else if (entry.name.endsWith(".md")) {
        docs.push(full);
      }
    }
  };
  walk(root);
  return docs.sort();
}

function main(argv) {
  const here = dirname(fileURLToPath(import.meta.url));
  const positional = argv.filter((a) => !a.startsWith("--"));
  const root = resolve(positional[0] ?? join(here, ".."));
  const strict = argv.includes("--strict");
  if (!existsSync(root)) {
    console.log(JSON.stringify({ error: `目录不存在：${root}` }, null, 2));
    return UNVERIFIED;
  }

  const docs = scan(root);
  const errors = [];
  const warns = [];
  let commandLines = 0;
  let proseLines = 0;

  for (const file of docs) {
    const rel = relative(root, file);
    const lines = readFileSync(file, "utf8").split("\n");
    // 文件级标记：H1 里说明这份文件是本机快照（如 toolchain.md）
    const h1 = lines.find((l) => l.trim().startsWith("# ")) ?? "";
    const fileMarked = MARKED.test(h1);
    let inFence = false;
    let sectionMarked = fileMarked;

    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];
      const at = `${rel}:${i + 1}`;

      if (raw.trim().startsWith("```")) {
        inFence = !inFence;
        continue;
      }

      if (!inFence && /^#{2,6}\s/.test(raw)) {
        sectionMarked = fileMarked || MARKED.test(raw);
        continue;
      }

      const line = maskDefaults(raw);
      // 行内标记（如「（本机：~/.dsh）」）与段落标记同等有效
      const marked = sectionMarked || MARKED.test(raw);
      const identities = [...line.matchAll(IDENTITY)].map((m) => m[0]);
      if (identities.length > 0) {
        // 身份路径没有豁免：即使在「本机快照」里也不该写别人的用户名
        errors.push(`${at}: 身份路径写进了文档 -> ${identities.join(", ")}`);
        continue;
      }

      const hosty = [...line.matchAll(HOSTY)].map((m) => m[0]);
      if (hosty.length === 0) {
        if (inFence) commandLines++;
        else proseLines++;
        continue;
      }

      if (inFence) {
        commandLines++;
        // PATH 前缀这类「可覆盖默认值」应写成 ${VAR:-/usr/local/bin}；写死就是 ERROR
        errors.push(`${at}: 命令里写死了宿主路径 -> ${hosty.join(", ")}（改成 \${VAR:-…} 或占位符）`);
      } else {
        proseLines++;
        // 标记过的段落/行（本机/快照/已实测）里出现本机路径是允许的，不作判定
        if (!marked) {
          warns.push(`${at}: 散文里的本机路径不在「本机/快照」段落里 -> ${hosty.join(", ")}`);
        }
      }
    }
  }

  if (docs.length === 0) {
    console.log(JSON.stringify({
      root, verdict: "UNVERIFIED", docs: 0,
      reason: "没有扫到任何 .md：本次校验的输入集为空，结论只能是未校验",
    }, null, 2));
    return UNVERIFIED;
  }

  const failed = errors.length > 0 || (strict && warns.length > 0);
  console.log(JSON.stringify({
    root,
    verdict: failed ? "FAIL" : "OK",
    docs: docs.length,
    commandLines,
    proseLines,
    errors,
    warnings: warns,
  }, null, 2));
  return failed ? BAD : OK;
}

process.exit(main(process.argv.slice(2)));
