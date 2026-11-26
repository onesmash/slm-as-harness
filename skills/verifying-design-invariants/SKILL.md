---
name: verifying-design-invariants
description: "把一条设计不变量押送到线上代码：S0 选点 + 五站（建模/桥接/守门/上线/收口），每站一个出口判据，不满足不许进下一站。Use when a design invariant must hold in shipped code — invariant checking, property-based testing, PlusCal/TLA+/TLC model checking, replaying a TLC counterexample against real code, a destruct variant that must go red, liveness/fairness, trace validation, Apalache. 触发词：形式化验证、不变量建模、模型检查、反例回放、模型和代码对不上。Do not use for one-off correctness checks, performance numbers (benchmark-checklist), or plain code review (review-nex)."
---

# 把设计不变量押送到线上

模型检查只能证明「模型里没有反例」。这条流程管的另一件事：**保证模型里的那句话就是代码里的那句话**，并且在代码改动后继续被守住。

要回答的就是那句老问题：设计验证很有价值，可**被发出去的是实现，不是设计**——设计级规格怎么接到实现上？（这句话在 AWS 的形式化实践材料里被反复引用，具体出处未核到原文，此处只当问题用，不当引文。）

## 什么时候用

- 有一条性质（不变量、顺序约束、幂等性、视图一致性、不重复用号）要在代码里长期守住，且**坏了很贵、测试又摸不到**
- 已经有人在跑 TLC，但没人能说清模型和代码哪一行对应
- 有人报「模型检查通过」「压测也做了」，你要判断这句话值多少

**不用**：一次性算对结果（那是普通测试）｜只关心性能数字（`benchmark-checklist`）｜纯代码审查（`review-nex`）｜设计阶段选型（那还没到这条流程）。

## 流程：S0 前置 + 五站

**S0 选点是前置筛选，不单独算一站**——它决定「做不做」，不产出模型。名字叫五站，指 S1–S5。

| 站 | 动作 | 出口判据（不满足不许进下一站） | 产物 |
|---|---|---|---|
| **S0 选点** | 只挑「坏了最贵 × 测试最摸不到」的性质 | 每条性质一句话、一个 owner、覆盖的文件/函数、sync commit | 性质登记表（`templates/property-register.md`） |
| **S1 建模** | 先画图让人确认转移对不对，再写模型：默认手写 TLA+ 加显式 `pc`，也可用 PlusCal（多实例进程写 `process P \in {1,2}`，**不写括号**；见 `examples/param-process/`） | ①**见过它失败**（每条性质一个破坏变体，且报红）②反例能读成人话的步骤序列 ③bounds 写清 | `.tla` / `.cfg` / `chart.mmd` / 反例轨迹 |
| **S2 桥接** | 把 TLC 反例**逐步**映射成真实调用 | 同一条违规在真实代码上有**可重放**的失败用例；复现不出 → 先疑模型，不是先疑代码 | 失败用例（先红） |
| **S3 守门** | ub-mode：先写会失败的测试，亲眼看它按预期理由失败 | ①红是**预期那个**理由 ②变绿 ③「全函数返回空时这条测试仍然失败」 | 提交 + why / what / how proved |
| **S4 上线** | 用规格校验真实日志（不需额外埋点），或断言常开 | 能报出**模型未覆盖**的行为；报出即回 S1 改模型 | 日志对规格的报告 / 线上断言 |
| **S5 收口** | 三句话 + 覆盖记录 + 重跑入口 | 下一个人不看对话也能一条命令重跑并对表（见下「六条判据」）；代码变了标 pending，或按「漂移后的维护」前移 sync commit | README + sync commit + 命令 |

**可重跑的六条判据**（全文见 `references/stations.md` 的 S5 节）：①–④ 是核心，下面逐条写；⑤「证据命令落成仓库脚本」与⑥「观察值不算证据」是延伸：① 干净 shell 里能跑；② **不依赖调用方 shell 里已有的环境变量**——宿主/CICD 常已占用 `HOME`、`DSH_HOME`、`CI` 这类名字，自己的脚本要用私有前缀，并在开头校验关键路径存在，找不到就报「找错目录」而不是报「数据不足」；③ 贴**真实跑出来的**退出码，不是预计的；④ 从零（空输出目录）**跑一次就 exit 0**。做不到就先想办法把第二次跑消灭掉——让脚本自己建基线，而不是把「要跑两次」写进文档；把重复动作写进文档，等于把负担转给下一个人。

**证据脚本统一用 0/1/2 三态退出码**：`0` 通过、`1` 失败（有反例/有对不上的步）、`2` 未判定（证据不足，既不是通过也不是失败）。三态分开是刻意的——CI 里非 0 都算不通过，但报告里必须写清是「错了」还是「证不了」，两者的下一步完全不同。

**观察值不算证据**：随输入增长的数字（步数、行数、条数、日志长度）只能记为带时间戳的观察，**不许挂在「守住」下面**。`守住` 只挂离散判定：退出码、反例有无、断言红绿。试点里同一条性质 21:49 是 1,718 步、22:17 是 1,768 步、22:22 是 1,774 步——数字会自己长大，它证不了任何东西。

每站的做法、证据形态和常见假通过，见 `references/stations.md`。

## 五道横切纪律

1. **每层失败必须是不同的失败。** S3 报的和 S1 报的是同一件事，就砍掉一层——重复劳动只提供安全感。
2. **一条性质只有一个 owner。** 模型、测试、运行监控引用同一句性质原文，不是三种转述。
3. **模型不许当文档。** 验收靠反例与回放，不靠「我建了模」。
4. **不许用测试结果反推模型正确。** TLC 过了是模型过，不是系统过。
5. **一个证据文件只有一个 owner。** 多人分别写各自分区的独立文件，合并由单一整合人做；**改任何既有文件前先读**（多人分工时最常见的损失是把别人的产物当空文件覆盖，而且往往没有 git 可恢复）。

## 多人分工时怎么摆

一个人做，五站串行就行。**一个团队做，先定谁签哪一站**，否则最后没人对整张表负责：

| 角色 | 管哪站 | 签什么 |
|---|---|---|
| 建模 | S1 | 破坏变体、退出码、bounds、数据形状假设 |
| 测试 | S2 / S3 | 反例逐步映射、三条守门门、头注释四段 |
| 收口 | S4 / S5 | 真实日志三种判定、一条命令重跑 |
| 交叉验收（只读） | 全部 | 复跑机器输出、对表、**只报矛盾** |

- **一个证据文件只有一个 owner**：各自写分区文件，合并由签名表里那一人做。
- **交叉验收要复跑，不要读结论**：试点里正是这一步抓到 PR 正文四个行号全错——作者自己看不见，因为他读的是自己的判断。
- **验收者不改文件**：只报矛盾。让他动手，他就会开始为自上一版辩护。
- **验收输出必须有命令和真实退出码**：写「我核过了」不算；写「跑了 X，exit 1，第 4 步对不上」才算。
- 格式照 `templates/verification-record.md`（签名表 + 各站分区 + 范围声明 + 机器核对输出）。

**新增一条规则时**，它必须能指到一次具体事故（`references/pilot-findings.md` 里的某条摩擦，或某次真实的报红/误判）。指不出出处的新规则只是偏好，偏好要删——技能靠「删掉不再需要的规则」保持可读，不是靠越写越多。

## 交之前跑机器核对

```sh
node <skill>/scripts/check-register.mjs <property-register.md> --root <仓库根>
# exit 0 = 表读得进来，且证据都指得到东西，且覆盖文件在 sync commit 之后没动过
# exit 1 = 有 ERROR 或硬告警：状态多值 / 表格中间中断（第二张表也不行）/ 等级词汇不对 /
#          编号重复 / 守住缺证据或 commit / 未判定没写理由 / 引用的文件不存在 / 代码文件名没有目录前缀 /
#          覆盖文件在 sync commit 之后有改动（含未提交）/ 承诺变更证据指不到东西 /
#          守住 行的 sync commit 零样本未核（不在 git 工作区，或覆盖列解析不出源码文件）
# exit 2 = 文件读不到、找不到表头，或表里没有任何可判定的证据引用（零样本 = 未校验，不是通过）
# 它不执行命令：「退出码」列是自述。--strict 再把风格类 WARN（没写范围等）也算失败；
# --allow-unverified-git 显式放行「确无 git」的环境——默认不放行，放行得是写出来的选择。
# 证据引用带不带目录前缀都核：带前缀按路径解析，不带前缀按文件名在仓库里找一遍
#（守住 行的每个文件名都必须翻得到；未判定 行还没落地的命令不报）。
```

它检查三件事：「表能不能被机器读」「证据指不指得到东西」「**覆盖文件在 sync commit 之后动过没有**」（拿 git 核，未提交也算；不是 git 工作区就明说未核，**零样本不算通过**）。它会**先打印证据候选数**（`evidence_candidates`）：候选为 0 时结论是「未校验」而不是「通过」——空模板、全是占位行的表，都在这一档。**不检查性质对不对、也不替你跑命令**——那两件事只能靠破坏变体与 CI。把 `exit 0` 读成「证据跑过」是过度解读；它能保证的是下一个人按表去翻不会扑空。

人眼核对不算核对：试点里状态列塞了整句、备注与表内互相打架、19 行的表被空行截成 9 行却仍报 OK，都是跑这一步（或它的下一版）才暴露的。

## 三个坑（都有出处）

- **trace validation 会假通过。** 日志不全时可能被错误接受，极端情形「只记录执行长度」也能通过 ⟹ S4 第一件事是证明**日志够细**，不是看它通过。（文献同一结论：埋点不足的 trace 太容易被接受，见 [viaduct: connecting formal models to production implementations](https://github.com/airbnb/viaduct/blob/main/core/engine/runtime2/lean/impldocs/old/connecting-formal-models-and-proofs-to-production-implementations.md)；线上系统里 trace validation 的假阳性主要来自记错值和不可靠剪枝，见 [USENIX ATC'25 CONVEROS](https://www.usenix.org/system/files/atc25_full_proceedings_interior.pdf)。）
- **trace validation 失败时没有反例。** 没有单条行为能解释失败，TLC 只能给一条最大有限行为 ⟹ S4 的报告要写「在哪一步对不上」，不能写「反例见附件」。（[arXiv:2404.16075](https://arxiv.org/abs/2404.16075) 把这条写进了 `TraceAccepted` 的定义里：失败时不存在能解释它的单条行为。）
- **CI 里的 TLC 要钉版本。** 钉 JRE 与 tla2tools 的 checksum，不依赖 runner 自带的 Java，否则换个 runner 就静默换解释器。
  传参时注意**变量名必须用工具真正读的那两个**：`statechart` 只认 `JAVA` 与 `TLA2TOOLS`（源码 `run.ts:194-195`）。如果你的 CI 里习惯叫 `JAVA_BIN` / `TLA2TOOLS_JAR`，加一行映射再调：`JAVA="$JAVA_BIN" TLA2TOOLS="$TLA2TOOLS_JAR" ...statechart`。设错名字不会报错，它会回落到 `mise install`——正是这一节要防的那种静默。

## 怎么跑（本机默认值已实测；换机器只改那几个变量）

```sh
# 换机器只改这几行；本机取值与版本见 references/toolchain.md
export PATH=${NODE_BIN:-/usr/local/bin}:$PATH          # statechart 要 Node 22.18–22.x 或 ≥23.6
export JAVA=${JAVA:-/usr/bin/java}        # JDK 21+
export TLA2TOOLS=${TLA2TOOLS:-$HOME/tools/tla/tla2tools.jar}
export SC=${SC:-$HOME/.agents/skills/statechart/scripts/statechart}

# S1：模型 + 图 + 最短违规路径，一条命令
cd <模型目录>
"$SC" SPEC.tla --config SPEC.cfg --out out/
# 规则全守住 → exit 0；任何规则破 → exit 1（statechart 归一化成 1；裸 TLC 是 12/13，见 toolchain.md）

# 只想跑 TLC、不要图：
"$JAVA" -XX:+UseParallelGC -cp "$TLA2TOOLS" tlc2.TLC -workers auto -config SPEC.cfg SPEC.tla
```

```sh
# 改过这个技能本身之后（先 cd 到技能目录），四件事全跑：
PATH=${NODE_BIN:-/usr/local/bin}:$PATH node --test scripts/check-register.test.mjs \
  scripts/check-register.contract.test.mjs scripts/check-guards.test.mjs \
  scripts/s5-clean-shell.test.mjs scripts/check-examples.test.mjs
# 0 = 全绿（46 条）。注意 `node --test scripts/` 这种目录写法在 Node 23 上会 MODULE_NOT_FOUND，
# 必须逐个点名——所以下面这些命令是唯一入口，别在别处再手敲一版。

# 交叉引用：反引号里的技能自有路径还指得到吗
PATH=${NODE_BIN:-/usr/local/bin}:$PATH node scripts/check-paths.mjs
# 0 = 有候选且引用全部解析；1 = 断链或有没人引用的文档；2 = 候选数为 0（未校验，不是通过）

# 可移植性：本机信息有没有被写进文档（身份路径 / 命令里的宿主路径 / 未标记段落里的本机事实）
PATH=${NODE_BIN:-/usr/local/bin}:$PATH node scripts/check-portability.mjs
# 0 = 干净；1 = 命令里写死宿主路径或出现身份路径（--strict 时 WARN 也算失败）；2 = 没扫到文档

# 示例还能不能跑（会真的起 TLC；任一未判定也是 2）
PATH=${NODE_BIN:-/usr/local/bin}:$PATH node scripts/check-examples.mjs
# 0 = 全 PASS；1 = 有示例不符预期；2 = 未判定/零示例
```

版本、`statechart` 不吃序列变量（会把模型跑崩）、TLC 的 `-workers` 与「状态数不是可复现量」——全部只在 `references/toolchain.md` 里维护，正文不再复述（同一件事写两遍，迟早一处改一处漏）。

**冒烟测试（改这个技能前先跑一遍）**：三对可跑的例子——
- `examples/view-window/`：`bash examples/view-window/run.sh` → 0（正确版 5 状态 / 4 条边 + 破坏变体报红）
- `examples/liveness/`：`bash examples/liveness/run.sh` → 0（公平版守住 + 抽掉 `WF_vars` 后 `AlwaysEventuallyReady was violated`）
- `examples/log-check/`：PASS / FAIL（指到步号与字段）/ UNDECIDED（缺字段）三个判定，退出码 0 / 1 / 2
前两个 runner 在临时目录里跑模型，技能树保持只读（跑完树哈希不变）。命令与预期输出写在各目录的 `README.md`。

## 跟已装判据技能怎么配合（别抄，直接调）

- **S3 之前与 S5 之前**：`principle-prove-it-works`——验的是真东西，不是代理指标、自述或「编译过了」。
- **要报任何数字**：`principle-explain-the-number` + `benchmark-checklist`——先说清限制它的是什么，再排除「它测的不是你以为的那件事」。
- **同一条提醒写第二遍时**：`principle-encode-lessons-in-structure`——把它变成 lint / 元数据位 / 运行时检查 / 脚本，而不是更多文字。
- **要画图**：`statechart`。

## 交付前自证

**A verify skill that was never run is a draft.** 同理，一条从没见过失败的性质不算被验证过：每条性质都要有一个破坏变体，并且你**亲眼**见它按预期理由报红。没红过的检查证明不了它有分辨力。

破坏变体按性质类型分两种，别混：
- **安全性质**（不变量）：改一行逻辑，让不变量必须被违反 → `examples/view-window/`
- **活性性质**（`[]<>`、`<>[]`、`PROPERTY`）：抽掉 `WF_vars`/`SF_vars` 公平性，让 TLC 找到「永远 stutter」的反例 → `examples/liveness/`

收口写给下一个人三句话：这条性质是什么、哪个命令能重跑、现在覆盖到哪个 commit。三句写不出来，说明它还没收口。

**检查器要能失败，也要报出输入集。** 输入集为空的检查必然通过：我用一次性命令数 markdown 链接，这个技能里那种链接 0 条，于是「断链 0、退出 0」看起来通过了，其实什么也没检查。所以自建检查器一律**先打印候选数**，零样本报「未校验」，并给它单独的退出码——不许把它并进「通过」。

**本机信息只有三个合法位置**：变量默认值 `${VAR:-…}`、占位符（`<仓库根>`、`<技能目录>`）、以及标注了「本机/快照/已实测」的段落或行内括号。命令正文里出现 `/usr/...`、`/opt/...`、`~/...` 就是 ERROR——换个人、换台机器就跑不起来。判据要按**类**判，不能按某个字符串判：`grep '/Users/'` 只抓得住「用户名绝对路径」一种形状，抓不住 `~/tools`、`/usr/local/bin`、`/opt/homebrew`，也抓不住把本机事实写进散文。`scripts/check-portability.mjs` 就是按这四类判的。

## 终态

这条流程的终态四个，收口时必须落到其中之一：

- `completed`：五站走完，S5 三句话 + 一条命令重跑 + sync commit 齐备
- `degraded_completed`：部分站只有观察级证据（如 S4 无日志面），降级理由与缺口写明
- `routed`：性质归邻居技能（纯测试 / benchmark / 代码审查），或 S0 判定不建模不进五站
- `unexecuted`：工具链缺失（Java / tla2tools.jar / node），证据命令 exit 2 未判定

## 细节（按需打开）

- `references/stations.md` — 五站逐站（S0 是前置筛选）：动作、证据形态、常见假通过
- `references/gates.md` — 七条质量门，当 S5 的验收契约
- `references/toolchain.md` — 本机已核实的路径/版本、CI 钉版本配方、Apalache 切换条件
- `references/example-ledger-view.md` — 我们那条 `room.log → ledger 视图` 补丁的完整映射
- `templates/property-register.md` — 性质登记表模板（状态单值 + 范围 + 证据等级 + 退出码）
- `templates/verification-record.md` — 多主体分工的签名表与分区格式
- `references/pilot-findings.md` — 一次真实多主体试点的十条摩擦，以及每条改成了什么结构
- `scripts/check-register.mjs` — 登记表机器核对器（exit 0/1/2；表格中断/证据指空 = 1；零候选 = 2）
- `scripts/check-register.contract.test.mjs` — 把上面那张退出码表变成可执行断言：文档说 exit 几，测试就要求 exit 几（零样本、裸文件名、参数顺序都在内）
- `scripts/check-guards.test.mjs` — 两个守卫核对器的行为锁：`check-paths` 的断链/孤儿/零候选/悬空指路，`check-portability` 的四类本机信息与 `${VAR:-…}` 豁免
- `scripts/s5-clean-shell.test.mjs` — S5 判据 ①④ 的行为锁：`env -i` 干净 shell 跑三个核对器；示例从零连跑两次都是 0 且不留中间产物
- `scripts/check-paths.mjs` — 交叉引用核对器（exit 0/1/2；候选 0 = 未校验）
- `scripts/check-portability.mjs` — 本机信息核对器（身份路径/命令里的宿主路径 = ERROR；未标记段落里的本机事实 = WARN）
- `scripts/check-examples.mjs` — 示例核对器：跑遍每个示例目录下的 `run.sh`，三态聚合（任一 FAIL = 1；任一未判定或零示例 = 2；全 PASS = 0）；**缺 runner 的示例报未判定并指名**，不静默跳过
- `examples/view-window/` — 可跑的冒烟测试（正确版 / 破坏变体）
- `examples/liveness/` — 活性性质的破坏变体：抽掉公平性
- `examples/param-process/` — 参数化进程（一个算法 N 个实例）：`process P \in {1,2}` 不写括号；抽掉 `await` 守卫即破
- `examples/log-check/` — S4 的最小可用日志校验器（Node，无依赖）
