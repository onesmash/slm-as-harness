// S5「可重跑」里那两条最难自动化的判据，这里各补一条行为测试：
//
//   摩擦 10（试点原文）：「有人报一条命令可重跑，但只在作者自己的 shell 里成立」
//     → 判据 ① 干净 shell 能跑。做法：用 `env -i` 起一个只剩 PATH 的环境，跑三个核对器。
//
//   摩擦 4（试点原文）：「文档写 ./run-s4.sh → exit 0，实际全新输出目录第一次必然 exit 2」
//     → 判据 ④ 从零跑一次就 exit 0。做法：同一个示例连跑两次，两次都必须 0，
//       且不许留下中间产物（「第二次才通过」这件事不许存在）。
//
// 跑：node --test scripts/s5-clean-shell.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(HERE);
const NODE_DIR = dirname(process.execPath);

// 干净环境：只有 PATH，没有任何自家变量（DSH_HOME / REFLEX_HOME / NODE_BIN …）
function cleanEnv() {
  return { PATH: [NODE_DIR, "/usr/bin", "/bin", "/usr/sbin", "/sbin"].join(":") };
}

function runClean(script, args) {
  const r = spawnSync("node", [join(HERE, script), ...args], {
    cwd: ROOT,
    encoding: "utf8",
    env: cleanEnv(),
  });
  return { code: r.status, out: r.stdout, err: r.stderr };
}

test("S5①：干净 shell 里三个核对器照常工作（不依赖调用方 shell 的变量）", () => {
  const paths = runClean("check-paths.mjs", []);
  assert.equal(paths.code, 0, `check-paths 在干净 shell 里应 exit 0，得到 ${paths.code}；${paths.err}`);
  assert.match(paths.out, /"candidates"/);

  const port = runClean("check-portability.mjs", ["--strict"]);
  assert.equal(port.code, 0, `check-portability --strict 应 exit 0，得到 ${port.code}；${port.err}`);
  assert.match(port.out, /"docs"/);

  // 空模板在干净 shell 里同样必须是「未校验」，不能被环境变量哄成通过
  const reg = runClean("check-register.mjs", [join(ROOT, "templates", "property-register.md")]);
  assert.equal(reg.code, 2, `空模板应 exit 2，得到 ${reg.code}；${reg.err}`);
  assert.match(reg.out, /UNVERIFIED|evidence_candidates/);
});

test("S5④：示例从零连跑两次都是 0，且不留中间产物（「要跑两次」不许存在）", () => {
  const script = join(ROOT, "examples", "log-check", "run.sh");
  assert.ok(existsSync(script), `找不到示例 runner：${script}`);

  for (const attempt of [1, 2]) {
    const r = spawnSync("bash", [script], { cwd: ROOT, encoding: "utf8" });
    assert.equal(r.status, 0, `第 ${attempt} 次跑应 exit 0，得到 ${r.status}；${r.stdout}${r.stderr}`);
    assert.match(r.stdout, /PASS/);
  }

  // log-check 的 runner 会写 *.out 再删；跑完目录里只该剩源文件与日志样本
  const leftovers = readdirSync(join(ROOT, "examples", "log-check")).filter((f) => f.endsWith(".out"));
  assert.deepEqual(leftovers, [], `跑完留下了中间产物：${leftovers.join(", ")}`);
});
