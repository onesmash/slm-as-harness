# skill-index 实现计划

**配套规格：** [2026-05-15-skill-index-design.md](2026-05-15-skill-index-design.md)
**日期：** 2026-05-15
**状态：** Draft

## 0. 实现前验证（必做）

在写任何代码前，**在本地真机上**确认 qmd 当前版本的 CLI 真实面：

```bash
npm install -g @tobilu/qmd
qmd --help
qmd collection --help
qmd collection add --help
qmd update --help
qmd embed --help
qmd query --help
```

把每个子命令的真实位置参数、flag 名、长短形式记录到 `scripts/lib_skill_index.py` 顶部 docstring。规格中假设的命令名（`qmd collection add <path> --name --mask`、`qmd update`、`qmd embed`、`qmd query "<q>" --collection`）若有偏差，**先在 docstring 修正，再写实现**。

## 1. 目录脚手架

```bash
mkdir -p slm-as-harness/skills/skill-index/scripts
touch slm-as-harness/skills/skill-index/SKILL.md
touch slm-as-harness/skills/skill-index/scripts/__init__.py
touch slm-as-harness/skills/skill-index/scripts/lib_skill_index.py
touch slm-as-harness/skills/skill-index/scripts/add.py
touch slm-as-harness/skills/skill-index/scripts/index.py
touch slm-as-harness/skills/skill-index/scripts/search.py
mkdir -p slm-as-harness/skills/skill-index/tests
touch slm-as-harness/skills/skill-index/tests/__init__.py
touch slm-as-harness/skills/skill-index/tests/test_lib_skill_index.py
touch slm-as-harness/skills/skill-index/tests/test_add.py
touch slm-as-harness/skills/skill-index/tests/test_index.py
```

## 2. 阶段化交付

### Phase 1 — 共享库 `lib_skill_index.py`（含单测）

**实现：**

1. 常量：`REPOS_DIR`、`CARDS_DIR`、`COLLECTION`、`SKILL_GLOB`、`CARD_GLOB`、`QMD_NPM_PKG`
2. `derive_name(git_url: str) -> str`
   - 算法：`url.rstrip('/').removesuffix('.git')`，取最后一段（按 `/` 或 `:` 优先 `/`，无 `/` 则 `:`）
   - 异常：空字符串或派生名为空 → `ValueError`
3. `parse_skill_frontmatter(path: Path) -> dict | None`
   - 用 `re` 而非 PyYAML 依赖：匹配首块 `---\n...\n---`
   - 提取 `name:` 和 `description:`（支持 `description: >` 多行折叠）
   - 缺字段返回 `None`
4. `ensure_qmd() -> None`
   - `shutil.which("qmd")`；缺则 `subprocess.run(["npm", "install", "-g", QMD_NPM_PKG], check=True)`
   - `npm` 缺失 → `FileNotFoundError`，由调用方 stderr 报错 + exit 1
5. `run_qmd(*args: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess`
   - 单一 qmd 调用包装；所有外层调用经此函数
6. `write_card(source: str, name: str, description: str, skill_md_path: Path) -> Path`
   - 写 `CARDS_DIR / source / f"{name}.md"`，含 frontmatter + 描述正文
   - 自动 `mkdir -p` 父目录

**测试 `tests/test_lib_skill_index.py`：**

- `test_derive_name_table` — 参数化覆盖：
  ```
  ("git@git.zoom.us:ai-tools/skills.git", "skills"),
  ("https://github.com/anthropics/skills.git", "skills"),
  ("https://github.com/foo/bar",            "bar"),
  ("git@host:user/multi/level/repo.git",    "repo"),
  ("https://example.com/x/", "x"),
  ```
- `test_derive_name_empty_raises`
- `test_parse_skill_frontmatter_happy` — 用 tmp_path 写一个合法 SKILL.md
- `test_parse_skill_frontmatter_missing_name_returns_none`
- `test_parse_skill_frontmatter_no_frontmatter_returns_none`
- `test_parse_skill_frontmatter_multiline_description` — `description: >` + 三行
- `test_write_card_creates_parent_dirs` — 用 tmp_path monkeypatch `CARDS_DIR`

**完成标准：** `pytest tests/test_lib_skill_index.py -q` 全绿。

---

### Phase 2 — `add.py`

**实现 `scripts/add.py`：**

```
main(argv):
    if len(argv) != 2: print usage → exit 2
    git_url = argv[1]
    ensure_qmd()
    name = derive_name(git_url)
    target = REPOS_DIR / name
    if target.exists():
        print(f"error: {target} already exists; rm -rf to re-add", file=sys.stderr)
        exit 1
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", git_url, str(target)], check=True)
    print(f"added {name} → {target}")
    print("next: /skill-index index")
```

**测试 `tests/test_add.py`：**

- `test_add_clones_bare_fixture` —
  - 用 `tmp_path` 创建 bare repo `fixture.git`（含 1 个假 SKILL.md）
  - monkeypatch `REPOS_DIR` 到另一个 tmp_path
  - 跑 `main(["add.py", f"file://{fixture.git}"])`
  - 断言 `REPOS_DIR / "fixture" / "SKILL.md"` 存在
- `test_add_duplicate_fails` — 第二次 add 同 URL → exit 1
- `test_add_bad_url_fails` — `file:///nonexistent` → exit 非零

**完成标准：** 上述测试全绿；手测一次真实 git URL。

---

### Phase 3 — `index.py`

**实现 `scripts/index.py`：**

```
main(argv):
    source_filter = argv[1] if len(argv) >= 2 else None
    ensure_qmd()

    sources = [source_filter] if source_filter else
              [p.name for p in REPOS_DIR.iterdir() if p.is_dir()]

    for source in sources:
        process_source(source)

    sync_qmd_collection()

process_source(source):
    src_root = REPOS_DIR / source
    found_cards: set[str] = set()
    counts = {added:0, updated:0, removed:0, skipped:0}

    for skill_md in src_root.glob("**/SKILL.md"):
        meta = parse_skill_frontmatter(skill_md)
        if meta is None or not meta.get("name") or not meta.get("description"):
            print(f"skip (missing frontmatter): {skill_md}", file=sys.stderr)
            counts.skipped += 1
            continue
        card_path = write_card(source, meta["name"], meta["description"], skill_md)
        found_cards.add(card_path.name)
        counts[added if newly_created else updated] += 1

    # orphan cleanup
    src_cards_dir = CARDS_DIR / source
    if src_cards_dir.exists():
        for existing in src_cards_dir.glob("*.md"):
            if existing.name not in found_cards:
                existing.unlink()
                counts.removed += 1

    print(f"{source}: +{added} ~{updated} -{removed} skip={skipped}")

sync_qmd_collection():
    out = run_qmd("collection", "list", capture=True).stdout
    if COLLECTION not in out:
        run_qmd("collection", "add", str(CARDS_DIR),
                "--name", COLLECTION, "--mask", "**/*.md")
    run_qmd("update")
    run_qmd("embed")
    print("qmd index synced")
```

**测试 `tests/test_index.py`：**

- `test_index_happy_path` —
  - 用 tmp_path 搭一个 `REPOS_DIR/fake/skill-a/SKILL.md` + `skill-b/SKILL.md`，frontmatter 齐
  - monkeypatch `REPOS_DIR` / `CARDS_DIR`
  - mock `run_qmd` 为 stub（避免依赖真实 qmd）
  - 跑 `main(["index.py"])`
  - 断言 `CARDS_DIR/fake/skill-a.md`、`skill-b.md` 存在；frontmatter 含 `source: fake` + `skill_md_path` 绝对路径
  - 断言 mock `run_qmd` 被调用顺序：`collection list` → `collection add ...`（首次）→ `update` → `embed`
- `test_index_missing_frontmatter_skipped` — 一个 SKILL.md 缺 `description` → 跳过 + stderr 警告
- `test_index_orphan_cleanup` — 预先放一个 `CARDS_DIR/fake/zombie.md`，跑 index 后该文件应被删
- `test_index_idempotent_second_run` — 第二次跑 `collection list` 已含 `skill-index`，不再调 `collection add`
- `test_index_specific_source` — `main(["index.py", "fake"])` 只处理 `fake` 不动其他

**完成标准：** 测试全绿；手测：真实仓库 + 真实 qmd。

---

### Phase 4 — `search.py`

**实现 `scripts/search.py`：**

```
main(argv):
    if len(argv) < 2: print usage → exit 2
    query = " ".join(argv[1:])
    ensure_qmd()
    # 透传 stdout/stderr，不捕获，保留 qmd 的 ANSI 色和可点击链接
    result = subprocess.run(
        ["qmd", "query", query, "--collection", COLLECTION],
        check=False
    )
    sys.exit(result.returncode)
```

**测试 `tests/test_search.py`：**

- `test_search_invokes_qmd_with_args` — mock subprocess.run，断言参数列表
- `test_search_no_query_exits_2`

**完成标准：** 测试绿；手测：先有索引后跑 `search "github"`。

---

### Phase 5 — `SKILL.md` + 端到端冒烟

**`SKILL.md` 内容：**

- Frontmatter 见规格 §6
- 正文章节：
  1. **What this skill does** —— 一段总述
  2. **Subcommands** —— 表格列 `add` / `index` / `search` 用法 + 例子
  3. **Dispatch logic** —— 写给 agent：解析 `$ARGS` 第一个 token 作为子命令，剩余作为参数，调用 `python3 scripts/<sub>.py <rest>`；未知子命令 → stderr + exit 2
  4. **What gets indexed** —— 说明合成卡机制 + frontmatter 字段要求
  5. **State locations** —— `~/.skill-index/repos/`、`~/.skill-index/available_skills/`、`~/.cache/qmd/index.sqlite`
  6. **First-run notes** —— 首跑会自动 `npm install -g @tobilu/qmd`
  7. **Limits** —— 引规格 §3 不包含部分

**端到端冒烟（手测脚本，记到 README 顶部）：**

```bash
/skill-index add git@git.zoom.us:ai-tools/skills.git
/skill-index index
/skill-index search "github MR review"
```

期望：search 命中 `helper-gitlab` 或同类技能。

---

## 3. 工作量估算

| Phase | 估时 | 备注 |
|---|---|---|
| 0 — qmd CLI 验证 | 15 分 | 跑 help，记录差异 |
| 1 — lib + 单测 | 60 分 | 主要在 `derive_name` 和 frontmatter 解析 |
| 2 — add | 30 分 | 含 bare repo 夹具 |
| 3 — index | 90 分 | 最重，含孤儿清理 + qmd 同步 |
| 4 — search | 15 分 | 薄包装 |
| 5 — SKILL.md + 冒烟 | 30 分 | |
| **总计** | **~4 小时** | |

## 4. 验收清单

实现完成时下列应全部 ✅：

- [ ] `pytest skills/skill-index/tests/ -q` 全绿（单测 + 集成）
- [ ] `qmd` 在干净机器上首跑能自动安装
- [ ] `/skill-index add <git-url>` 能 clone 到 `~/.skill-index/repos/<name>/`，重复 add 报错不覆盖
- [ ] `/skill-index index` 能为每个 SKILL.md 生成合成卡，孤儿卡片自动清理
- [ ] `/skill-index index` 首跑 bootstrap qmd 集合，二跑不重复 `collection add`
- [ ] `/skill-index search "<query>"` 透传 qmd 输出含可点击链接
- [ ] 所有 qmd 调用经由 `lib_skill_index.run_qmd`
- [ ] 缺 frontmatter 的 SKILL.md 跳过 + stderr 警告，不阻断其他技能
- [ ] 失败场景按规格 §4.4 表正确 stderr + exit 非零（fail-loud）

## 5. 提交策略

按 phase 分别 commit，每个 commit 含「实现 + 对应测试」：

1. `feat: skill-index — shared lib + frontmatter parser`
2. `feat: skill-index — add subcommand (git clone)`
3. `feat: skill-index — index subcommand (cards + qmd sync)`
4. `feat: skill-index — search subcommand (qmd query passthrough)`
5. `feat: skill-index — SKILL.md dispatch + smoke test`

每个 commit message 末尾标准 Co-Authored-By。
