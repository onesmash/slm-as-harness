---
name: code-kb-stage-4-qa
description: Run stage 4 of the code knowledge-base workflow. Use when the user wants to QA an existing `knowledge-base/`, verify whether it can answer real repository or source-corpus questions, validate the `knowledge-base/llms.txt` discovery surface, detect stale pages after recent commits or source ingests, or turn question failures into a concrete maintenance loop. This stage primarily invokes `wiki-qa`, escalating to `wiki-researcher` for deeper gaps and using `wiki-changelog` to detect freshness drift.
---

# Code KB Stage 4: QA

Load (read all of these before grading — invoked-skill contracts are non-negotiable and *not* duplicated in this file):

- [../references/source-context.md](../references/source-context.md)
- [../references/artifact-contract.md](../references/artifact-contract.md)
- [../references/stage-4-qa-feedback.md](../references/stage-4-qa-feedback.md)
- [../references/maintenance-loop.md](../references/maintenance-loop.md)
- [../wiki-page-writer/SKILL.md](../wiki-page-writer/SKILL.md) — **required**. Same per-page format contract Stage 3 was supposed to honor; Stage 4 grades against it independently so a page that slipped through Stage 3 is caught here, not in production.
- [../wiki-qa/SKILL.md](../wiki-qa/SKILL.md) — **required**. Has a `Source Context Resolution (MUST DO FIRST)` section and defines how questions must be answered with grounded source analysis. Stage 4's tested questions in `04-qa-feedback.md` are answered using this skill's discipline.
- [../wiki-researcher/SKILL.md](../wiki-researcher/SKILL.md) — required when a tested question needs deeper tracing than the page already provides. Has `Core Invariants (NON-NEGOTIABLE)` rules.
- [../wiki-changelog/SKILL.md](../wiki-changelog/SKILL.md) — required when checking freshness or when recent commits drive a stale-page finding. Has a `Source Repository Resolution (MUST DO FIRST)` section.

## Goal

Test whether the current knowledge base is usable, current, and worth trusting.

## Execution Rules

- Resolve source context before QA if citation style matters.
- Read the current `knowledge-base/` pages first.
- Use `wiki-qa` to answer real repo or corpus questions against the existing knowledge base and source files.
- Use `wiki-researcher` only when the answer needs deeper tracing than the page already provides.
- Use `wiki-changelog` when git history exists and freshness or recent-change drift is part of the question; otherwise use source-ingestion history or `knowledge-base/log.md`.
- When `knowledge-base/llms.txt` exists, validate its link coverage, path correctness, and freshness against the current page set.
- **Run [`../scripts/check_page_format.py`](../scripts/check_page_format.py) on `knowledge-base/` and treat its output as a graded dimension, not a one-off check.** Stage 3 is also supposed to run it, but Stage 4 is the safety net that catches what Stage 3 missed. A content-correct page that fails the linter loops back to Stage 3 — do not file it as `published`.

## Minimum Output

Write or refresh:

- `knowledge-base/_meta/04-qa-feedback.md` — must include a `## Format compliance` section reporting the output of `scripts/check_page_format.py knowledge-base/ --json` (per-page pass/fail with the rule ids that fired). Pages with errors loop back to Stage 3; pages with only warnings can be published with the warnings called out.
- one QA artifact under `knowledge-base/qa/`. The QA artifact itself must satisfy the per-page format contract (frontmatter + `## Related Pages` table at minimum — Mermaid quotas are relaxed for QA artifacts).

Each issue must name the repair path: rerun Stage 1, Stage 2, or Stage 3.

## Finalize: Strip U+FE0F

After QA writes are done, run the variation-selector strip pass over `knowledge-base/` so QA artifacts do not carry invisible `U+FE0F` codepoints. See the orchestrator's Output Hygiene section for the rationale.

```bash
python3 ../scripts/strip_vs16.py knowledge-base/
```

## Handoff

Turn QA failures into explicit backlog actions instead of vague "needs improvement" notes.
