---
name: code-kb-workflow
description: "Build, optimize, and maintain a long-lived `knowledge-base/` for a code repository or other source corpus through four independently runnable stages: source reading, writing-plan, page writing, and QA feedback. Use this whenever the user wants a repo wiki, a source-grounded knowledge base, onboarding guides, changelog-backed refreshes, an LLM-readable `knowledge-base/llms.txt` surface, or a durable documentation maintenance loop. Also use this when the user only knows the end goal and needs the workflow to decide which stage to run next."
---

# Code Knowledge Base Workflow

Use this skill as the orchestrator for a multi-skill documentation pipeline. The default delivery surface is `knowledge-base/`, with workflow state stored in `knowledge-base/_meta/`. It is optimized for code repositories, but it can also bootstrap and maintain a knowledge base grounded in a document corpus, research set, or mixed evidence collection when the user still wants durable `knowledge-base/` artifacts.

This workflow is intentionally split into four stages so each one can run alone:

| Stage | Skill | Required contracts | Conditionally required | Main output |
|------|-------|--------------------|------------------------|-------------|
| 1 | `code-kb-stage-1-read-code` | one of `read-code-workflow` / `read-paper-workflow` (chosen by source-context type) | `wiki-researcher` (when escalating a deep trace) | `knowledge-base/_meta/01-reading-note.md` |
| 2 | `code-kb-stage-2-plan` | `wiki-architect` (every plan; defines the catalogue structure including the "Onboarding section first, uncollapsed" mandate) | `wiki-onboarding` (when planning onboarding pages); `wiki-changelog` (when source history is in scope) | `knowledge-base/_meta/02-catalogue-plan.md`, `knowledge-base/_meta/03-page-backlog.md` with LLM-surface coverage decisions |
| 3 | `code-kb-stage-3-write` | `wiki-page-writer` (every published page; defines frontmatter / Mermaid / `## Related Pages` table contract) | `wiki-onboarding` (when writing onboarding pages); `wiki-changelog` (when writing changelog pages); `wiki-llms-txt` (when generating `llms.txt`) | Pages under `knowledge-base/`, `knowledge-base/llms.txt`, plus backlog updates |
| 4 | `code-kb-stage-4-qa` | `wiki-page-writer` (the format rubric Stage 4 grades against) and `wiki-qa` (the question-answering discipline) | `wiki-researcher` (when a tested question needs deep tracing); `wiki-changelog` (when freshness drift is the question) | `knowledge-base/_meta/04-qa-feedback.md`, `knowledge-base/qa/` |

Each stage's `SKILL.md` has a `Load:` block that lists every required and conditionally-required skill above with one-line context. **Read every required-contract skill's `SKILL.md` before performing the stage.** Past runs have shipped output that was content-correct but format-incomplete because the stage SKILL was read while the contract skill it invokes was not — the contract skill carries `MUST DO FIRST` / `NON-NEGOTIABLE` rules that the stage SKILL does *not* duplicate. See `## Common Pitfalls` below.

## First Move

Before choosing a stage, resolve four things in order:

1. What repository or source corpus is in scope.
2. Whether it is local-only or has a canonical remote or source URL.
3. Whether the user wants the full four-stage run, one explicit stage, or a specific output such as onboarding pages, changelog pages, or `llms.txt` artifacts.
4. Which durable workflow artifacts already exist under `knowledge-base/` and `knowledge-base/_meta/`.

If source context is missing, load [references/source-context.md](references/source-context.md) and resolve it before applying routing rules.

After source context is known, explicit user intent outranks heuristic routing:

- If the user asks for the whole workflow, run `1 -> 2 -> 3 -> 4` in order.
- If the user names a stage explicitly, run only that stage and preserve other stage artifacts.

## Routing Rules

- No `knowledge-base/` exists yet and `knowledge-base/_meta/01-reading-note.md` does not exist -> Stage 1.
- The user says "start from understanding the code" or "start from understanding the source material" and `knowledge-base/_meta/01-reading-note.md` does not exist -> Stage 1.
- The user asks to restart from understanding the code or source material but `knowledge-base/_meta/01-reading-note.md` already exists -> ask whether they want to reread and overwrite Stage 1 outputs or continue from Stage 2.
- A reading note exists and the page structure is weak, the catalogue does not make sense, or `02-catalogue-plan.md` / `03-page-backlog.md` is missing, empty, or stale -> Stage 2.
- The user asks for onboarding guides, changelog pages, or other written pages and both `02-catalogue-plan.md` and `03-page-backlog.md` exist -> Stage 3.
- The user asks for onboarding guides, changelog pages, or page refreshes and a reading note exists but planning artifacts do not -> `2 -> 3`.
- The user asks for onboarding guides, changelog pages, or named page output with no durable workflow artifacts yet -> `1 -> 2 -> 3`.
- The user asks for `llms.txt` or other LLM-readable knowledge-base discovery files and both `02-catalogue-plan.md` and `03-page-backlog.md` exist -> Stage 3.
- The user asks for `llms.txt` or other LLM-readable knowledge-base discovery files and a reading note exists but planning artifacts do not -> `2 -> 3`.
- The user asks for `llms.txt` or other LLM-readable knowledge-base discovery files with no durable workflow artifacts yet -> `1 -> 2 -> 3`.
- The user scopes work to one subsystem, source batch, or a mixed "read one area, refresh another" request -> prefer a partial path such as `1 (partial) -> 2 (partial) -> 3 -> 4` instead of restarting the whole corpus.
- Pages exist and the user asks if the knowledge base is correct, stale, or complete -> Stage 4.

Representative examples:

- "Start from understanding the code, but we already have a reading note." -> clarify whether to reread Stage 1 or continue from Stage 2.
- "The reading note exists but the page structure is weak." -> Stage 2.
- "Build an onboarding guide for new engineers." -> `1 -> 2 -> 3`, `2 -> 3`, or `3` depending on which prerequisite artifacts already exist.
- "Refresh docs for the payments module and reread only the checkout flow." -> partial maintenance path, not a full restart.

## Long-Term Maintenance Policy

- Never rewrite the whole `knowledge-base/` by default when only one subsystem changed.
- Use `wiki-changelog` to narrow refresh scope before planning or QA whenever recent commits matter.
- Treat `knowledge-base/_meta/03-page-backlog.md` as the durable queue of pages to create, revise, or retire.
- Treat Stage 4 findings as the source of truth for what must loop back to Stage 1, 2, or 3.
- Treat `knowledge-base/llms.txt` as a derived discovery artifact that should be refreshed whenever the page set or page hierarchy changes materially.
- When bootstrapping a new knowledge base, treat adjacent control artifacts such as `raw/`, `AGENTS.md`, `knowledge-base/index.md`, `knowledge-base/log.md`, and `knowledge-base/llms.txt` as first-class parts of the system.
- Treat repo-root `AGENTS.md` as healthy only when it contains one populated, managed `code-kb` block delimited by `<!-- code-kb:start -->` and `<!-- code-kb:end -->`. Do not leave the marker pair empty; write the actual workflow guidance using [references/managed-agents-block-template.md](references/managed-agents-block-template.md).
- When refreshing repo-root `AGENTS.md`, prefer updating only the content inside the managed `code-kb` block and leave unrelated sections outside the markers untouched.
- A bootstrap run is not complete without a root `AGENTS.md` whose managed `code-kb` block tells future agents how to maintain the knowledge base.

Load these references as needed:

- [references/workflow-map.md](references/workflow-map.md)
- [references/artifact-contract.md](references/artifact-contract.md)
- [references/maintenance-loop.md](references/maintenance-loop.md)
- [references/managed-agents-block-template.md](references/managed-agents-block-template.md) when bootstrapping or refreshing repo-root `AGENTS.md`

## References

Every contract file below is loaded by path; the stage skills link them as `../references/…` because
they live one directory deeper. Start here when you need the detail behind a routing decision:

| File | What it holds |
|---|---|
| `references/workflow-map.md` | The four-stage map, what each stage consumes and produces, and where the loop returns |
| `references/source-context.md` | How to resolve and record source context before routing (corpus root/type/mode, citation style) |
| `references/artifact-contract.md` | The per-page contract every published page must satisfy (frontmatter, Mermaid, sources, Related Pages) |
| `references/maintenance-loop.md` | The long-term loop: what to re-run when sources change, and how QA feedback returns to reading/planning |
| `references/managed-agents-block-template.md` | Template for the managed `code-kb` block in a repo-root `AGENTS.md` |
| `references/stage-1-code-reading.md` | Stage 1 contract: the evidence package, downscope rules, and the handoff block |
| `references/stage-2-writing-plan.md` | Stage 2 contract: catalogue plan, page backlog, and LLM-surface coverage decisions |
| `references/stage-3-page-writing.md` | Stage 3 contract: page writing order, format gates, and backlog updates |
| `references/stage-4-qa-feedback.md` | Stage 4 contract: the question set, failure classification, and feedback that loops back |

The two scripts are run, not read: `scripts/check_page_format.py` gates format compliance and
`scripts/strip_vs16.py` removes variation selectors from published pages.

## Output Contract

At minimum, this workflow should leave behind one durable artifact the next stage can reuse. That means one of:

- a fresh reading note,
- a catalogue plan and page backlog,
- one or more written pages or LLM-readable discovery surfaces,
- or a QA report with concrete follow-up actions.

Do not stop at verbal guidance if the user asked to run the workflow.

## Output Hygiene

Two scripted hygiene passes run after Stage 3 writes pages and after Stage 4 writes QA artifacts. Both must pass before declaring the stage done.

### 1. Format compliance — `check_page_format.py`

Every published page under `knowledge-base/` must satisfy the per-page contract enumerated in [`references/artifact-contract.md`](references/artifact-contract.md) → `## Minimum Content Requirements` → "any published page under `knowledge-base/`". The contract is sourced from [`wiki-page-writer/SKILL.md`](wiki-page-writer/SKILL.md): VitePress frontmatter, 3-5 dark-mode Mermaid diagrams mixing ≥2 types with `autonumber` on sequences, `<!-- Sources: -->` after each diagram, "Source" column on listing tables, and a `## Related Pages` table at the end.

Past Stage 3 runs have shipped pages that were content-correct but format-incomplete because the orchestrator and the stage-3 SKILL describe the *flow* while `wiki-page-writer/SKILL.md` describes the *page format*; an agent that reads the stage SKILLs but skips `wiki-page-writer/SKILL.md` ends up writing prose-only pages. The linter mechanically catches that failure mode — Stage 3 cannot ship, and Stage 4 cannot grade-as-passing, a page that fails it.

```bash
python3 path/to/code-kb-workflow/scripts/check_page_format.py knowledge-base/
```

The script is non-destructive (read-only). It exits non-zero when any published page has a hard violation; warnings on `index.md`/`README.md` (where the Mermaid quota is heuristic) do not fail the run. JSON output is available via `--json` for programmatic consumption (e.g., piping into Stage 4's `04-qa-feedback.md` § Format compliance section). See [scripts/check_page_format.py](scripts/check_page_format.py).

### 2. Variation-selector strip — `strip_vs16.py`

Generated `knowledge-base/` files should not contain `U+FE0F` (Variation Selector-16, VS16). VS16 is a zero-width Unicode codepoint that follows dual-presentation characters such as `⚠` (U+26A0), `✅` (U+2705), and `❌` (U+274C) to force colored emoji rendering. Models tend to emit it because the public web overwhelmingly uses the FE0F-decorated form, but in a knowledge base it is undesirable: it is invisible yet inflates byte counts, breaks naive char-based diffs, makes documents look noisy in hex-aware tools, and adds platform-dependent rendering. Prefer the bare codepoint and let the renderer pick its own presentation.

Two practical rules:

- When writing a page yourself, just emit the bare character (`⚠`, `✅`, `❌`). Do not hand-append the variation selector. Tokenizer priors will still slip some FE0F through — that is fine, the next rule cleans it up.
- After Stage 3 writes pages, and after Stage 4 writes QA artifacts, run the strip pass before declaring the stage done:

  ```bash
  python3 path/to/code-kb-workflow/scripts/strip_vs16.py knowledge-base/
  ```

  The script is idempotent and skips non-text files. See [scripts/strip_vs16.py](scripts/strip_vs16.py).

If a renderer truly requires emoji presentation in one specific spot, prefer a single-codepoint emoji (e.g. `🚨` U+1F6A8 instead of `⚠️`) so no variation selector is needed.

## Managed AGENTS Block Template

When bootstrapping or refreshing repo-root `AGENTS.md`, load [references/managed-agents-block-template.md](references/managed-agents-block-template.md) and use it as the starting point for the managed `code-kb` block. Customize only the repo-specific details that truly differ.

## Common Pitfalls

These are failure modes that have happened on past runs. Naming them here so the *next* run doesn't repeat them.

- **Treating "primarily invokes" as "optional helper".** Each stage SKILL names downstream skills (`wiki-page-writer`, `wiki-architect`, `wiki-onboarding`, `wiki-changelog`, `wiki-llms-txt`, `wiki-qa`, `wiki-researcher`, `read-code-workflow`, `read-paper-workflow`). All of those carry `MUST DO FIRST` / `NON-NEGOTIABLE` contracts that the stage SKILL does not duplicate. The stage SKILL describes the *flow*; each invoked skill describes the *output format or method*. **Read every required-contract skill listed in the stage's `Load:` block before doing the stage's work.** Skipping is the canonical way to ship output that is content-correct but format-incomplete.

- **Writing pages from prose-and-citations alone.** A page that has well-grounded prose and accurate `file:line` citations but lacks frontmatter, Mermaid diagrams, and a `## Related Pages` table is *half* the contract, not "good enough for a first edition". Stage 3 must run [`scripts/check_page_format.py`](scripts/check_page_format.py) and resolve every error before flipping a backlog row from `planned` to `drafted`; Stage 4 grades the same script's output as a required dimension.

- **Producing a catalogue that doesn't put Onboarding first.** `wiki-architect/SKILL.md` mandates that the generated catalogue **MUST include an Onboarding section first and uncollapsed**. Stage 2's `02-catalogue-plan.md` `## Page Hierarchy` must reflect this, and the eventual `knowledge-base/index.md` must too. Architecture-first / components-first orderings violate the contract even when they look natural.

- **Skipping `Source Repository Resolution (MUST DO FIRST)` because the stage SKILL already mentioned source context.** Each `wiki-*` skill has its own `Source Context Resolution (MUST DO FIRST)` section with skill-specific resolution rules. The stage SKILL's "resolve source context first" rule is necessary but not sufficient.

- **Filing a page as `published` while the linter still reports errors.** A page that fails [`scripts/check_page_format.py`](scripts/check_page_format.py) loops back to Stage 3 even when its content is correct. The backlog status flow is `planned` → (write) → linter → (clean) → `drafted` → (Stage 4 graded) → `published`.

- **Letting `_meta/` artifacts use repo-root-relative paths and forgetting to flag the convention in QA.** `_meta/01-reading-note.md` cites repo files repo-root-relatively (e.g. `App/Core/Auth.swift`); published pages cite them document-relatively (`../../App/Core/Auth.swift`). Both are intentional, but Stage 4 must say so explicitly so the next maintenance run does not "fix" the convention by accident.

## When Not To Use

Do not use this skill for:

- one-off prose documentation unrelated to a source corpus,
- a pure code question that does not need a knowledge-base artifact,
- a pure PR review,
- or a general research task with no `knowledge-base/` outcome.

For those, route directly to the narrower skill instead of forcing the whole workflow.
