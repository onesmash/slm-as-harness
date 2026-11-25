# 本机工具链：已核实的路径、版本与硬约束

写这份文件的规矩：**每个路径和版本都是在本机跑出来的**，不是抄博客。没装的就写「未装」，不写成「默认有」。

## 已装并实测（2026-11-22 21:0x）

| 件 | 位置 | 版本 / 大小 |
|---|---|---|
| Java | `/usr/bin/java` | Temurin **21.0.13+9**（2026-10-20 LTS） |
| TLA+ 工具 | `~/tools/tla/tla2tools.jar` | 4,510,915 B；`TLC2 Version 2026.11.19.180144 (rev: bc1b506)` |
| Node（statechart 需要） | `/usr/local/bin/node` | v23.11.0（符号链接到 Homebrew Cellar） |
| Bun（备选运行时） | `/usr/local/bin/bun` | 1.2.7 |
| statechart | `~/.agents/skills/statechart/scripts/statechart` | SKILL.md 9,069 B + scripts/ |

**注意**：非交互 shell 里 `/usr/local/bin` 不一定在 PATH 上，所以命令要带 `PATH=${NODE_BIN:-/usr/local/bin}:$PATH`（本机 Homebrew 前缀作默认值，换机器设 `NODE_BIN`），否则 statechart 找不到 Node 会直接报错（它要求 Node 22.18–22.x / ≥23.6、Bun ≥1.1.5 或 Deno ≥2.0）。

表里是**本机快照**，不是要求别人照抄的路径：下面的命令一律用可覆盖的变量（`PATH` / `JAVA` / `TLA2TOOLS` / `SC`），换机器只改那几个变量，不改正文，也不把某个人的家目录写进技能。

## 未装（别写成默认有）

| 件 | 状态 | 什么时候才装 |
|---|---|---|
| Apalache | **本机未装**（`which apalache-mc` 空，`~/tools` 下无目录） | TLC 状态爆炸、跑不完，或需要归纳不变量时。它是**同一模型的另一个后端**，不是重写模型 |
| Quint | 未装 | 只在团队已有 Quint 习惯时；换语法不换语义，我们不引 |
| fast-check | **本机任何项目都没有**（`~/.dsh/bot/workspace` 与 `~/SourceCode/*/node_modules` 均无） | S2 要回放时随项目 `npm i -D fast-check` 装上 |
| PObserve | 未装 | S4 需要把日志对规格时；它是 P 生态的，Node 侧没有对等物。本机先用 `examples/log-check/check-log.mjs`（无依赖，PASS/FAIL/UNDECIDED 三判定） |

## 两条命令（都实测过）

### 1. statechart：模型 + 图 + 最短违规路径

```sh
cd <模型目录>
export PATH=${NODE_BIN:-/usr/local/bin}:$PATH
export JAVA=${JAVA:-/usr/bin/java}
export TLA2TOOLS=${TLA2TOOLS:-$HOME/tools/tla/tla2tools.jar}
export SC=${SC:-$HOME/.agents/skills/statechart/scripts/statechart}
"$SC" SPEC.tla --config SPEC.cfg --out out/
```

- **退出码可当门，但两套码不一样**（实测，别混）：
  | 跑法 | 通过 | 不变量违反 | 时序性质违反 |
  |---|---|---|---|
  | `statechart` 一条命令 | 0 | 1 | 1 |
  | 裸 `tlc2.TLC` | 0 | **12** | **13** |
  CI 里统一按「非 0 即不通过」判，别断言等于 1——裸 TLC 的 12/13 会让 `exit == 1` 写成永远不成立的判据。
- 它优先读 `TLA2TOOLS` + `JAVA` 两个环境变量（源码 `run.ts:194-195`）；不设就走 `mise install`，那需要网络
- 产物：`out/chart.mmd`、`out/report.md`、`out/tlc.out`
- 不写 `--view` 时，图上标签是变量赋值原文（`view="empty" pc="idle"`）。要给人看，写 view 模块导出 `state()` / `step()`
- 图有 500 状态预算，超了只画违规路径；规则破了之后每次重跑限 100,000 个状态

### 2. 纯 TLC：只要判定，不要图

```sh
"$JAVA" -XX:+UseParallelGC -cp "$TLA2TOOLS" \
  tlc2.TLC -workers auto -config SPEC.cfg SPEC.tla
```

- **必须显式给 `-workers`**：TLC 默认 25% 内存 + **一个** worker
- **状态数不是可复现量（实测）**：同一份 `red038dual`，`-workers 1` 三跑全是 16 states / 9 distinct；`-workers auto` 三跑是 78/53、90/64、104/64——谁先撞到违规谁停，BFS 顺序随线程竞争变。所以：
  - 可承诺复现的是**退出码、违反的不变量名、反例序列**（这三样与 workers 无关）
  - 状态数必须连同 `-workers` 一起写，否则两个人报的「16」和「39」会互相判为矛盾——它们只是同一件事在两种调度下的快照
  - 要拿状态数当证据（覆盖率、界够不够），固定 `-workers 1`，并把它写进命令
- `-deadlock` 的语义是「**不要**检查死锁」，不是「检查死锁」
- 报错时会给状态序列与一条 `*_TTrace_*.tla` 轨迹文件，可直接喂回 TLC 复跑

## statechart 的五条硬约束（踩过就知道）

1. **状态变量必须是枚举型。** 放 `ledger \in Seq(...)` 会让它崩在 `Cannot read properties of undefined (reading 'tag')`（二分实测：同构的枚举版 3 状态通过，序列版必崩）。它的 33 个语料样例里 `Seq(` 出现 0 次——这条路径从来没被测过。要画图就把状态抽象成枚举，序列只留在 TLC 侧的不变量里。
2. **`Next` 必须是各动作的析取**，否则 TLC 把每一步都命名为 `Next`。
3. **终态要有动作。** 没有出边的状态会破 `NoDeadlock`，哪怕是正确的结束状态。**但 `CONSTRAINT` 截断不是死锁**：只要 `Next` 在该状态仍有可执行的动作，TLC 就不算死锁——它只是不展开违约的后继（`view-window` 例子里 `count=2, pc="ready"` 就是这种情况，`NoDeadlock` 成立是真的，不是被吞掉）。加一个只在终态为真、什么都不改的动作（`Done == pc \in {...} /\ UNCHANGED vars`），并在 `--view` 的 `step()` 里给它标签。
4. **别在仓库里跑。** 官方要求用仓库外的临时目录。实测在目录里跑会留下四种产物，都别进版本库：`out/`（statechart 的 chart/report/tlc.out）、`states/`（TLC 状态文件）、`<模块>_TTrace_*.tla|bin`（违规时的轨迹）。**examples/ 下两个模型各带自清 runner（`examples/liveness/run.sh`、`examples/view-window/run.sh`）：模型拷进临时目录跑，跑完技能树一字不变**——2026-11-24 有个子进程照旧 README 在树里跑 liveness，TLC 的 TTrace 直接写穿了一次 test-skill 的冻结快照。手动跑也照这个模式：拷出去、跑、删临时目录。

5. **Mermaid 标签只写 ASCII。** 非 ASCII 会被后端转成数字实体（`（` → `&#65288;`），图不报错、只是变得看不懂——这是「不崩但坏样」，比崩更难发现（崩了有人查，难看容易被当成没问题）。中文说明放在图外的正文里；状态名用英文动词短语（`configs on disk, source invisible`），别用变量名。

## CI 里钉版本（照抄会被解释器静默换掉）

- 钉 **JRE** 与 **tla2tools.jar** 的 checksum，不依赖 runner 自带的 Java
- 变量名用工具真正读的那两个：`statechart` 只认 `JAVA` / `TLA2TOOLS`（`run.ts:194-195`）。CI 里若习惯 `JAVA_BIN` / `TLA2TOOLS_JAR`，加一行映射：`JAVA="$JAVA_BIN" TLA2TOOLS="$TLA2TOOLS_JAR"`
- 升级 JRE 或 jar 时，把 TLC 版本号连同 checksum 一起写进提交信息——否则「通过」失去时间坐标

## fast-check `commands`（S2 回放用，本机未装）

装法：`npm i -D fast-check`（本机 npm 走 clash 代理 7897）。

契约：命令对象要 `check` / `run` / `toString`，模型侧 `modelRun`（同步）/ `asyncModelRun` / `scheduledModelRun`；失败给 `seed + path + replayPath`，shrink 只缩真正执行过的命令。

判据：它复现的必须是 **TLC 报的那条**违规，不是你以为的那条。
