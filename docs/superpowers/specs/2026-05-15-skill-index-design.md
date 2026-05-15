# skill-index 设计规格

**日期：** 2026-05-15
**状态：** Draft — 待规格评审
**作者：** hui.xu

## 1. 概要

`skill-index` 是 `slm-as-harness` 仓库中的一个新技能，用于把多个来源的「技能仓库」（skill / agent-skill repositories）聚合到本地一个可搜索的索引。

它向用户暴露三条斜杠子命令：

```
/skill-index add <git-url>      # clone 仓库到 ~/.skill-index/repos/<name>/
/skill-index index [source]     # 生成/刷新合成技能卡 + qmd 重建索引
/skill-index search <query>     # qmd 跨集合混合检索
```

底层使用 [tobi/qmd](https://github.com/tobi/qmd)（`@tobilu/qmd` npm 包）作为本地搜索引擎，索引数据落在 qmd 默认位置 `~/.cache/qmd/index.sqlite`。

## 2. 动机

用户同时关注多个技能仓库（`zoom-skills`、`anthropics/skills`、个人 skills 等），希望：

- 一处问「有没有干 X 的技能」就能跨所有仓库找到答案；
- 不依赖网络（在线 `npx skills find` 只能搜公开发布的技能，看不到内部仓库）；
- 搜索结果直接给出可点击的 `SKILL.md` 路径，能立刻打开看。

## 3. 范围

### 包含

- 克隆任意 git 仓库到 `~/.skill-index/repos/<derived-name>/`
- 遍历各克隆仓库内的所有 `SKILL.md`，解析 YAML frontmatter（`name`、`description`），生成合成技能卡
- 用 qmd 索引这些合成卡，提供混合（BM25 + 向量 + LLM 重排）搜索
- 首次运行时按需懒加载安装 qmd

### 不包含（YAGNI 显式排除）

- 单独的 `setup` / `list` / `remove` / `update` / `pull` 子命令
- 仓库分支 / `--depth` 配置
- **后台**自动定时刷新（cron / launchd）—— 用户主动跑 `/skill-index index` 时本技能即同步拉最新代码 + 再生卡片 + 重建索引；不另外起守护进程
- MCP server 接入（用户可自行用 `qmd mcp`）
- 重名冲突的解决 UI
- 索引到子技能文档（仅取 `SKILL.md` 自身的 frontmatter）

## 4. 关键设计决策

### 4.1 索引粒度：每技能一张合成卡

替代方案：

| 选项 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A. 单文件目录 | 全部技能堆一个 markdown | 一次写入 | qmd 按 ~900 token 切块；命中一块时无法确定具体技能 |
| **B. 每技能一卡** ✅ | `~/.skill-index/available_skills/<source>/<name>.md` | qmd 文档级评分自然适配；命中路径即技能 | 文件数多（但都极小） |
| C. 直接索引原 SKILL.md | qmd 吃 `repos/**/SKILL.md` | 含正文，语义匹配细 | 噪声大；正文长导致命中片段不直观 |

选定 **B**。

### 4.2 单一 qmd 集合

原方案是每个克隆仓库一个 qmd 集合（`skill-index:<source>`）。新方案改为单一集合 `skill-index`，覆盖 `~/.skill-index/available_skills/**/*.md`。

理由：
- 合成卡已按 `<source>/<name>.md` 分目录隔离，足够命名空间区分；
- 单集合更简单，搜索时不再需要通配 `--collection "skill-index:*"`；
- qmd 输出已包含路径，源信息自然可见。

### 4.3 状态唯一真相

- `~/.skill-index/repos/` 目录列表 = 已克隆仓库的唯一真相
- `~/.skill-index/available_skills/` 目录列表 = 应当被索引的技能卡的唯一真相
- `~/.cache/qmd/index.sqlite` = qmd 已索引内容的派生缓存；由 qmd 自管理，不归本技能直接维护

不维护额外 JSON 配置文件，避免三处状态同步漂移。当 `available_skills/` 与 qmd 索引内容偏离时，跑 `index` 即重新对齐。

### 4.4 失败语义：fail-loud

与同仓库的 `context-index`（fail-open 静默兜底）不同，`skill-index` 是用户主动调用的工具，错误必须暴露：

| 错误 | 行为 |
|---|---|
| `npm` 缺失或 qmd 安装失败 | stderr 解释 + `exit 1` |
| `git clone` 失败（`add`） | git 原生错误透传 + `exit 1` |
| `git fetch/reset` 失败（`index`） | stderr 报错 + 该 source 跳过本轮，其他 source 继续；`index` 末尾 `exit 0` 但摘要中标注失败计数 |
| 仓库名冲突（目录已存在） | stderr 报错 + `exit 1`，不覆盖 |
| 某个 SKILL.md 缺 frontmatter | stderr 警告 + 跳过该技能，其余继续 |
| qmd 子命令失败 | qmd 错误透传 + `exit 1` |

## 5. 架构

### 5.1 目录布局

```
/Users/hui.xu/SourceCode/slm-as-harness/skills/skill-index/
  SKILL.md
  scripts/
    lib_skill_index.py   # 共享：路径、URL→name、qmd 包装、frontmatter 解析
    add.py               # /skill-index add 的入口
    index.py             # /skill-index index 的入口
    search.py            # /skill-index search 的入口

~/.skill-index/                           # 运行时状态（非技能源码）
  repos/<source>/                         # 原始 git clone
    <skill-name>/SKILL.md
    ...
  available_skills/<source>/<name>.md     # 合成技能卡（qmd 实际索引对象）

~/.cache/qmd/index.sqlite                 # qmd 自管理，无需备份
```

### 5.2 合成技能卡格式

```markdown
---
name: foo
source: zoom-skills
skill_md_path: /Users/hui.xu/.skill-index/repos/zoom-skills/foo/SKILL.md
---

# foo

Does foo things — used when user wants to do foo.
```

- frontmatter 提供结构化三元组：`name`、`source`、`skill_md_path`
- body 复制自原 SKILL.md frontmatter 的 `description` 字段，供 qmd 做 BM25 / 向量匹配
- 文件名 `<name>.md`，源目录 `<source>/`

### 5.3 组件职责

#### `lib_skill_index.py`

共享常量与工具函数：

```python
REPOS_DIR     = Path.home() / ".skill-index" / "repos"
CARDS_DIR     = Path.home() / ".skill-index" / "available_skills"
COLLECTION    = "skill-index"
SKILL_GLOB    = "**/SKILL.md"

def derive_name(git_url: str) -> str: ...
def ensure_qmd() -> None: ...
def run_qmd(*args: str) -> subprocess.CompletedProcess: ...
def parse_skill_frontmatter(path: Path) -> dict | None: ...
def write_card(source: str, name: str, description: str, skill_md_path: Path) -> Path: ...
```

`derive_name` 算法：
1. 去掉尾部 `.git`
2. 取最后一段（按 `/` 或 `:` 分割）
3. 例：`git@git.zoom.us:ai-tools/skills.git` → `skills`，`https://github.com/anthropics/skills.git` → `skills`

`ensure_qmd`：`shutil.which("qmd")`；若缺则 `npm install -g @tobilu/qmd`，npm 缺失则 `exit 1`。

#### `add.py <git-url>`

1. `ensure_qmd()`
2. `name = derive_name(url)`
3. `target = REPOS_DIR / name`
4. 若 `target` 存在 → `exit 1`，提示用户手动 `rm -rf` 后重试
5. `git clone --depth 1 <url> <target>`
6. 打印 `added {name} → {target}`
7. **强制提示**用户接下来跑 `/skill-index index` 以生成合成卡 + 建索引（stdout 末行单独一句：`next: run "/skill-index index" to (re)generate skill cards and refresh the qmd index`）

`add` 不触发索引 —— clone 与 index 职责分离，便于用户连加多个仓库后一次性 index。每次 `add` 都必须打印 index 提示，避免用户忘记导致 search 命中为空。

#### `index.py [source]`

`index` 是「全量刷新」入口：先拉远端最新代码 → 清理失踪 source → 再生卡片 → 同步 qmd。

1. `ensure_qmd()`
2. 确定 sources：有参数 → 仅该 source；无参数 → `REPOS_DIR` 下所有子目录
3. **阶段 1 — git 刷新**：对每个 in-scope source，对 `REPOS_DIR / source` 跑：
   ```
   git -C <target> fetch --depth=1 origin HEAD
   git -C <target> reset --hard FETCH_HEAD
   ```
   失败（网络断、仓库 404、`.git` 不存在）→ stderr 报错 + 该 source 跳过本轮所有后续阶段，**不中断其他 source**
4. **阶段 2 — source 级孤儿清理**：遍历 `CARDS_DIR.iterdir()`，若某 `<source>` 子目录在 `REPOS_DIR/` 下已不存在（用户 `rm -rf` 过）→ `shutil.rmtree(CARDS_DIR/<source>)`
5. **阶段 3 — 卡片再生**：对每个仍在线的 source：
   a. `walk(REPOS_DIR / source, glob="**/SKILL.md")`
   b. 对每个 `SKILL.md`：解析 frontmatter；缺 `name` 或 `description` → stderr 警告 + 跳过
   c. 写卡片到 `CARDS_DIR / source / <name>.md`
6. **阶段 4 — 卡片级孤儿清理**：对比 `CARDS_DIR / source / *.md` 与本轮生成集合，删多余
7. **阶段 5 — qmd 集合同步**：
   a. 用 `qmd collection list` 检查是否已有名为 `skill-index` 的集合 —— 这是「集合是否已 bootstrap」的**唯一**判定来源，不在 `~/.skill-index/` 下落任何 sentinel 文件
   b. 若无 → `qmd collection add <CARDS_DIR> --name skill-index --mask "**/*.md"`（仅首次跑；后续轮次靠 `qmd update` 同步增量，不重复 `add`）
   c. 跑 `qmd update`（重扫文件系统，发现新增 / 删除 / 修改的 markdown）
   d. 跑 `qmd embed`（为新增 / 变更的文档生成向量嵌入，确保 vsearch / query 能命中）
8. 打印每个 source 的 `pulled/added/updated/removed/skipped` 计数，外加 source-级孤儿删除条目数

> **实现先验证：** qmd 仍在早期迭代，CLI 子命令面可能变。实现前先跑 `qmd --help`、`qmd collection --help`、`qmd update --help`、`qmd embed --help` 确认子命令与 flag 真实形态，并把所有 qmd 调用收敛在 `lib_skill_index.py` 的 `run_qmd(*args)` 包装中（参见 §8）。

#### `search.py <query>`

1. `ensure_qmd()`
2. `qmd query "{query}" --collection skill-index`（透传 qmd 默认输出格式：带 ANSI 色和可点击编辑器链接）
3. 不二次格式化，stdout 直透

### 5.4 数据流

```
git@host:org/repo.git
        │
        │ /skill-index add  (git clone --depth=1)
        ▼
~/.skill-index/repos/<source>/<skill>/SKILL.md   (原始 clone)
        ▲ │
        │ │ /skill-index index 阶段 1：
        │ │   git fetch --depth=1 origin HEAD
        │ │   git reset --hard FETCH_HEAD
        │ ▼
        └──┐
           │ /skill-index index 阶段 3：frontmatter 解析
           ▼
~/.skill-index/available_skills/<source>/<name>.md   (合成卡)
        │
        │ /skill-index index 阶段 5：qmd update + qmd embed
        ▼
~/.cache/qmd/index.sqlite   (BM25 + 向量索引)
        │
        │ /skill-index search "query"
        ▼
stdout   (带链接的结果)
```

## 6. SKILL.md 草稿

```yaml
---
name: skill-index
description: >
  Aggregate skill/agent repositories from multiple sources into one local
  searchable index. Clones repos to ~/.skill-index/repos/, generates synthetic
  per-skill cards from SKILL.md frontmatter, and indexes them with qmd
  (BM25 + vector hybrid search at ~/.cache/qmd/index.sqlite).

  Use this skill whenever the user wants to add a new skill source,
  rebuild the local skill index, or search across all known skill sources
  for "is there a skill for X" style questions across multiple internal /
  external skill repositories.

  Subcommands:
    add <git-url>       - clone a repo to ~/.skill-index/repos/<derived-name>/
    index [source]      - regenerate skill cards and refresh qmd index
    search <query>      - hybrid search across all indexed skills
---
```

正文部分说明三条子命令的用法、`derived-name` 规则、frontmatter 字段要求、qmd 索引位置等。

## 7. 测试策略

### 7.1 单元测试（pytest）

- `derive_name` —— 表驱动覆盖：
  - `git@git.zoom.us:ai-tools/skills.git` → `skills`
  - `https://github.com/anthropics/skills.git` → `skills`
  - `https://github.com/foo/bar` → `bar`（无 `.git`）
  - `git@host:user/multi/level/repo.git` → `repo`
- `parse_skill_frontmatter` —— 合法、缺字段、非 YAML、空文件四种 case

### 7.2 集成测试

用本地 bare repo 作为夹具：

1. 临时目录创建 `fake-skills.git` bare 仓库，含两个 `<skill>/SKILL.md`，frontmatter 齐全
2. 跑 `add.py file://...fake-skills.git`，断言 `~/.skill-index/repos/fake-skills/` 存在
3. 跑 `index.py`，断言 `~/.skill-index/available_skills/fake-skills/<name>.md` × 2 存在，frontmatter 正确
4. 跑 `search.py "foo"`，断言 stdout 含目标技能名

测试用 `tmp_path` fixture 重定向 `REPOS_DIR` / `CARDS_DIR`，避免污染真实 `~/.skill-index/`。

### 7.3 手测

`/skill-index add git@git.zoom.us:ai-tools/skills.git` →
`/skill-index index` →
`/skill-index search "github MR review"` →
验证返回 `helper-gitlab` 或 `ios-gitlab-merged-mr-review` 等命中。

## 8. 风险与未决

- **qmd 版本漂移：** qmd 还在早期开发，CLI 子命令命名可能变。所有 qmd 调用必须经由 `lib_skill_index.run_qmd(*args)` 单一包装函数，使外层逻辑用「意图」（如 `qmd_ensure_collection` / `qmd_reindex`）而非 CLI verb 表达；将来若 qmd 子命令改名，改一处即可。实现首日先跑 `qmd --help` 锁定当前真实子命令面，写到包装层注释里。
- **首次安装的 npm 依赖：** 用户机器若无 Node.js，`ensure_qmd` 会失败。可接受 —— 报错明确即可，安装 Node 不在本技能职责内。
- **大仓库 clone 时间：** 默认 `--depth 1`，几秒内完成；超大仓库由用户用 `cd repos/<name> && git fetch --unshallow` 补全。
- **重名仓库：** 当前用最末 path segment 派生名字，跨源同名仓库会冲突。报错让用户决定（重命名目录或先删旧）。该决策可在后续版本演进，不阻塞首版。

## 9. 后续可能（不在本规格）

- `remove <source>` / `list` 子命令（若用户实际需要）
- 卡片正文加入更多字段（`when_to_use` / `examples`）以提升语义匹配质量
- 与 `find-skills` 技能合并或互调
- 接入 qmd MCP，让 Claude Code 工具调用直接命中本地索引
