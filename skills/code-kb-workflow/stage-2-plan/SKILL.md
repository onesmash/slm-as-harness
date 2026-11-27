---
name: code-kb-stage-2-plan
description: Run stage 2 of the code knowledge-base workflow. Use when the user wants a wiki or `knowledge-base/` structure from a repository or source corpus, needs a page backlog, wants onboarding, changelog, or `llms.txt` coverage planned, or needs to refresh documentation scope after repository changes or source growth. This stage primarily invokes `wiki-architect`, with `wiki-onboarding` and `wiki-changelog` as planning extensions.
---

# Code KB Stage 2: Plan

Load (read all of these before producing the catalogue plan — invoked-skill contracts are non-negotiable and *not* duplicated in this file):

- [../references/source-context.md](../references/source-context.md)
- [../references/artifact-contract.md](../references/artifact-contract.md)
- [../references/stage-2-writing-plan.md](../references/stage-2-writing-plan.md)
- [../wiki-architect/SKILL.md](../wiki-architect/SKILL.md) — **required**. Has a `Source Context Resolution (MUST DO FIRST)` section and a structural mandate that the generated catalogue **must include an Onboarding section first and uncollapsed**. The page hierarchy you write into `02-catalogue-plan.md` and the eventual `knowledge-base/index.md` must honor this ordering.
- [../wiki-onboarding/SKILL.md](../wiki-onboarding/SKILL.md) — required when the plan calls for onboarding pages. Defines the four audience-tailored guides (Contributor, Staff Engineer, Executive, Product Manager) Stage 3 will need to produce. The `## Onboarding Coverage` section of `02-catalogue-plan.md` should reflect those audiences explicitly.
- [../wiki-changelog/SKILL.md](../wiki-changelog/SKILL.md) — required when source history is in scope (`## Changelog Coverage` non-empty). Has a `Source Repository Resolution (MUST DO FIRST)` section.

## Goal

Turn source understanding into a durable writing system.

## Execution Rules

- Resolve source context before invoking the wiki skills.
- Prefer reading `knowledge-base/_meta/01-reading-note.md` first when it exists.
- Honor the reading note's `## Handoff Status`; if the reading pass is partial or blocked, keep the plan scoped to what is actually supported and record what still needs more reading.
- Use `wiki-architect` to build the catalogue.
- Use `wiki-onboarding` when the corpus needs role-specific onboarding outputs, especially for code-heavy knowledge bases.
- Use `wiki-changelog` when git history exists and recent commits should influence priority or freshness; otherwise use source-ingestion history or `knowledge-base/log.md`.
- Plan whether Stage 3 should generate or refresh `knowledge-base/llms.txt` for LLM-readable discovery.

## Minimum Output

Write or refresh:

- `knowledge-base/_meta/02-catalogue-plan.md`
- `knowledge-base/_meta/03-page-backlog.md`

`knowledge-base/_meta/02-catalogue-plan.md` must include these exact top-level sections:

- `## Page Hierarchy`
- `## Writing Order`
- `## Evidence Sets`
- `## Onboarding Coverage`
- `## Changelog Coverage`
- `## LLM Surface Coverage`
- `## Bootstrap Decision`

The `## Bootstrap Decision` section must say whether Stage 3 must create or refresh repo-root `AGENTS.md`, name `AGENTS.md` as the target control file, and record the concrete Stage 3 action or explicit no-op rationale.

## Handoff

Mark which pages are ready for Stage 3 immediately, which ones still need more reading first, whether Stage 3 must generate or refresh `knowledge-base/llms.txt`, and whether Stage 3 must create or refresh repo-root `AGENTS.md`.
