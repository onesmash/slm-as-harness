#!/usr/bin/env node
// 用规格校验真实日志（S4 的最小可用骨架）。
//
// 用法：node check-log.mjs <spec.mjs> <log.jsonl>
//
// 退出码是有语义的，别当成普通 0/1：
//   0 = 每一步都对得上，且规则全守住   -> PASS
//   1 = 有步骤对不上，或规则被违反     -> FAIL（会指出第几步、哪个字段）
//   2 = 日志不足以判定（缺字段/缺动作）-> UNDECIDED，**不等于通过**
//
// spec.mjs 要导出：
//   initial    : 初始状态对象
//   compared   : 规格能算出来、必须与日志逐字段一致的字段名（旧名 required 也可，兼容）
//   loggedOnly : 规格不计算、只从日志取给规则用的字段名（可缺省）
//   actions    : { 动作名: (state, event) => nextState }
//   rules      : { 规则名: (observed) => boolean }，observed 来自日志，不是规格算出来的值
//
// 两套字段必须分清，这是本脚本唯一容易写错的地方：
//   把「规格不计算的字段」放进 compared -> compare 每步都报不符（expected 是 undefined）
//   把「规格应当算出来的字段」只放进 loggedOnly -> 规则读它，但没人比对它
// 缺任何一套里的字段 -> UNDECIDED（证据不全），不猜默认值。

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const PASS = 0;
const FAIL = 1;
const UNDECIDED = 2;

function fail(reason, extra = {}) {
  return { verdict: "FAIL", reason, ...extra };
}

function loadSpec(path) {
  return import(pathToFileURL(path).href);
}

function readLog(path) {
  const raw = readFileSync(path, "utf8");
  const lines = raw.split("\n").map((l, i) => ({ line: i + 1, text: l.trim() }))
    .filter((l) => l.text.length > 0);
  const events = [];
  for (const { line, text } of lines) {
    try {
      events.push(JSON.parse(text));
    } catch {
      return { error: fail(`日志第 ${line} 行不是合法 JSON`, { line }) };
    }
  }
  if (events.length === 0) return { undecided: "日志是空的：没有可判定的内容" };
  return { events };
}

// 两套字段：compared（要与规格比）与 loggedOnly（只给规则读）
const comparedFields = (spec) => spec.compared ?? spec.required ?? [];
const loggedOnlyFields = (spec) => spec.loggedOnly ?? [];
const allFields = (spec) => [...comparedFields(spec), ...loggedOnlyFields(spec)];

// 规格自检：这两类错在字段契约里最容易犯，开跑前拦住，别让它变成「假 PASS」
function specContractError(spec) {
  if (spec.compared && spec.required) {
    return "规格同时导出了 compared 与 required：请只留一个（required 是旧名）";
  }
  const overlap = comparedFields(spec).filter((f) => loggedOnlyFields(spec).includes(f));
  if (overlap.length > 0) {
    return `字段同时出现在 compared 与 loggedOnly：${overlap.join(", ")}（会被比对又喂给规则，语义不明）`;
  }
  return null;
}

// 粒度检查：动作名与两套字段缺一个，就说「不足以判定」，不猜。
// 缺 action 也属证据不全（不是「动作不在规格里」），否则会把日志残缺报成代码错。
function missingFields(spec, event) {
  const missing = allFields(spec).filter((f) => !(f in event));
  if (!("action" in event)) missing.push("action");
  return missing;
}

function applyAction(spec, state, event) {
  const action = spec.actions?.[event.action];
  if (!action) return { error: fail(`第 ${event.step ?? "?"} 步的动作 ${event.action} 不在规格里`, { step: event.step }) };
  try {
    return { state: action(state, event) };
  } catch (e) {
    return { error: fail(`第 ${event.step ?? "?"} 步动作执行失败：${e.message}`, { step: event.step }) };
  }
}

// 从日志事件里取出规则要读的字段，构造「日志声称的状态」。
// 注意：规则必须判定日志，不能判定规格自己算出来的值——后者是自证。
function observedState(fields, event) {
  const out = {};
  for (const f of fields) out[f] = event[f];
  return out;
}

// 返回 { broken: [规则名], errors: [规则名: 原因] }
// 规则不成立 = 违反；规则抛错 = 求值出错（另一种失败，报出来让人查，不吞）
function brokenRules(spec, observed) {
  const broken = [];
  const errors = [];
  for (const [name, rule] of Object.entries(spec.rules ?? {})) {
    try {
      if (!rule(observed)) broken.push(name);
    } catch (e) {
      errors.push(`${name}: ${e.message}`);
    }
  }
  return { broken, errors };
}

function compare(step, expected, logged, required) {
  const diffs = [];
  for (const f of required) {
    if (!(f in logged)) continue; // 已由粒度检查拦下
    const a = JSON.stringify(expected[f]);
    const b = JSON.stringify(logged[f]);
    if (a !== b) diffs.push({ step, field: f, expected: expected[f], logged: logged[f] });
  }
  return diffs;
}

function run(spec, events) {
  let state = spec.initial;
  const compared = comparedFields(spec);
  const fields = allFields(spec);
  for (const event of events) {
    const missing = missingFields(spec, event);
    if (missing.length > 0) {
      return { verdict: "UNDECIDED", step: event.step, reason: `缺少字段 ${missing.join(", ")}：日志不足以判定` };
    }
    const applied = applyAction(spec, state, event);
    if (applied.error) return applied.error;
    const diffs = compare(event.step, applied.state, event, compared);
    if (diffs.length > 0) {
      return fail(`第 ${event.step} 步与规格不符`, { step: event.step, diffs });
    }
    const observed = observedState(fields, event);
    const { broken, errors } = brokenRules(spec, observed);
    if (errors.length > 0) {
      return fail(`第 ${event.step} 步规则求值出错`, { step: event.step, errors });
    }
    if (broken.length > 0) {
      return fail(`第 ${event.step} 步违反规则 ${broken.join(", ")}`, { step: event.step, rules: broken });
    }
    // 期望值一律由规格推进：日志不回灌，避免日志给自己作证
    state = applied.state
  }
  return { verdict: "PASS", steps: events.length };
}

async function main(argv) {
  const [specPath, logPath] = argv;
  if (!specPath || !logPath) {
    console.error("用法：node check-log.mjs <spec.mjs> <log.jsonl>");
    return FAIL;
  }
  const spec = await loadSpec(specPath);
  const contractError = specContractError(spec);
  if (contractError) {
    console.log(JSON.stringify({ verdict: "FAIL", reason: contractError }, null, 2));
    return FAIL;
  }
  const read = readLog(logPath);
  if (read.undecided) {
    console.log(JSON.stringify({ verdict: "UNDECIDED", reason: read.undecided }, null, 2));
    return UNDECIDED;
  }
  if (read.error) {
    // 坏 JSON 是「证据本身不可用」，与 UNDECIDED（内容不足）和 FAIL（对不上）都不同，
    // 但必须挡住：静默跳过坏行等于让日志自己删证据。
    console.log(JSON.stringify(read.error, null, 2));
    return FAIL;
  }
  const result = run(spec, read.events);
  console.log(JSON.stringify(result, null, 2));
  if (result.verdict === "PASS") return PASS;
  if (result.verdict === "UNDECIDED") return UNDECIDED;
  return FAIL;
}

process.exit(await main(process.argv.slice(2)));
