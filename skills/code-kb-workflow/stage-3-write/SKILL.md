---
name: code-kb-stage-3-write
description: Run stage 3 of the code knowledge-base workflow. Use when the user wants actual pages written or refreshed under `knowledge-base/`, including architecture pages, component deep-dives, onboarding guides, changelog pages, `llms.txt` discovery files, or other source-grounded documentation. This stage primarily invokes `wiki-page-writer`, with `wiki-onboarding`, `wiki-changelog`, and `wiki-llms-txt` handling their specialized deliverables.
---

# Code KB Stage 3: Write

Load (read all of these before writing the first page — the per-page format contract is non-negotiable and is *not* duplicated in this file):

- [../references/source-context.md](../references/source-context.md)
- [../references/artifact-contract.md](../references/artifact-contract.md) — note especially the "any published page under `knowledge-base/`" subsection of `## Minimum Content Requirements`
- [../references/stage-3-page-writing.md](../references/stage-3-page-writing.md)
- [../wiki-page-writer/SKILL.md](../wiki-page-writer/SKILL.md) — **required for every published page**. Defines the page format every published page must satisfy: VitePress frontmatter, 3-5 dark-mode Mermaid diagrams mixing ≥2 types with `autonumber` on sequences, `<!-- Sources: -->` after each diagram, citation-density rules, "Source" column on listing tables, `## Related Pages` table at the end, escaped bare generics. Do not write a page from prose-and-citations alone — that is half the contract.
- [../wiki-page-writer/references/acceptance-criteria.md](../wiki-page-writer/references/acceptance-criteria.md) — concrete ✅/❌ examples for the rules above.
- [../wiki-onboarding/SKILL.md](../wiki-onboarding/SKILL.md) — required when writing onboarding pages. Has a `Source Repository Resolution (MUST DO FIRST)` section and defines the four audience-tailored guides (Contributor, Staff Engineer, Executive, Product Manager). Onboarding pages still satisfy `wiki-page-writer`'s page-format contract on top of `wiki-onboarding`'s structure.
- [../wiki-changelog/SKILL.md](../wiki-changelog/SKILL.md) — required when writing changelog pages or refresh summaries. Has a `Source Repository Resolution (MUST DO FIRST)` section and defines the change-categorization the changelog page must use.
- [../wiki-llms-txt/SKILL.md](../wiki-llms-txt/SKILL.md) — required when generating or refreshing `knowledge-base/llms.txt`. Has a `Source Repository Resolution (MUST DO FIRST)` section and defines the llms.txt format. `llms.txt` is plain-text and is exempt from the page-format rules; treat its own spec as the contract.

## Goal

Write the real `knowledge-base/` pages instead of stopping at a plan.

## Execution Rules

- Resolve source context before writing pages with citations.
- Read `knowledge-base/_meta/02-catalogue-plan.md` and `knowledge-base/_meta/03-page-backlog.md` first when they exist.
- **Every published page goes through `wiki-page-writer`'s contract** — it is required reading for *every* page kind (technical pages, onboarding pages, changelog pages, even a one-paragraph stub). The other writer skills below add page-kind-specific structure on top of that contract; they do not replace it.
- Use `wiki-onboarding` (loaded in the Load block above) for role-specific onboarding guides when the corpus warrants them.
- Use `wiki-changelog` (loaded above) for changelog pages or refresh summaries when change history is available.
- Use `wiki-llms-txt` (loaded above) when the plan or user asks for an LLM-readable discovery surface for the current knowledge base.
- Prefer updating existing pages over creating duplicates with overlapping scope.
- When bootstrapping a corpus-style knowledge base, write or refresh control artifacts such as `knowledge-base/index.md`, `knowledge-base/log.md`, or `AGENTS.md` when the plan calls for them.
- When the plan calls for LLM-readable delivery, refresh `knowledge-base/llms.txt`.
- Do not create `knowledge-base/llms-full.txt` or repo-root `llms.txt` from this workflow.
- If root `AGENTS.md` is missing during a bootstrap run, create it before considering Stage 3 complete.

## Minimum Output

Before finishing, do all of these:

1. write or materially refresh at least one real page under `knowledge-base/`, or generate or materially refresh at least one planned LLM-readable surface derived from the current page set,
2. **for every page written or refreshed in this run, satisfy the per-page format contract** in [`../references/artifact-contract.md`](../references/artifact-contract.md) `## Minimum Content Requirements` → "any published page under `knowledge-base/`",
3. run [`../scripts/check_page_format.py`](../scripts/check_page_format.py) on every written/refreshed page and resolve every reported violation before declaring the page `drafted` in the backlog (a page that does not pass the linter stays `planned`),
4. update backlog status in `knowledge-base/_meta/03-page-backlog.md`.

Additionally, if this is a bootstrap run and root `AGENTS.md` is missing or explicitly marked stale in the plan, create or refresh it.

## Finalize: Strip U+FE0F

After the page writes are done, run the variation-selector strip pass over `knowledge-base/` so generated pages do not carry invisible `U+FE0F` codepoints. See the orchestrator's Output Hygiene section for the rationale.

```bash
python3 ../scripts/strip_vs16.py knowledge-base/
```

The script is idempotent and only touches text files (`.md`, `.markdown`, `.txt`, `.mdx`). Run it from the repo root with the correct relative path to `code-kb-workflow/scripts/strip_vs16.py` for the current install.

## Handoff

Identify what should go to Stage 4 for QA next, including any newly generated `knowledge-base/llms.txt` surface.
