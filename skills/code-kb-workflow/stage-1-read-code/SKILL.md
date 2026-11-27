---
name: code-kb-stage-1-read-code
description: Run stage 1 of the code knowledge-base workflow. Use when the user wants to understand a repository or source corpus before writing docs, capture a durable reading note for `knowledge-base/_meta/01-reading-note.md`, or refresh understanding for only one subsystem or source cluster. This stage primarily invokes `read-code-workflow` for code repositories, `read-paper-workflow` for non-code source documents, and escalates to `wiki-researcher` when a key storyline needs deeper tracing across many files or sources.
---

# Code KB Stage 1: Read Evidence

Load (read all of these before producing the reading note — invoked-skill contracts are non-negotiable and *not* duplicated in this file):

- [../references/source-context.md](../references/source-context.md)
- [../references/artifact-contract.md](../references/artifact-contract.md)
- [../references/stage-1-code-reading.md](../references/stage-1-code-reading.md)
- [../read-code-workflow/SKILL.md](../read-code-workflow/SKILL.md) — methodology for code corpora; load when source-context is `code-repository` or the code half of a mixed corpus.
- [../read-paper-workflow/SKILL.md](../read-paper-workflow/SKILL.md) — methodology for non-code corpora (papers, RFCs, reports, design docs); load when source-context is `document-corpus` or the document half of a mixed corpus.
- [../wiki-researcher/SKILL.md](../wiki-researcher/SKILL.md) — **required if the reading pass needs to escalate**. Has a `Source Context Resolution (MUST DO FIRST)` section and `Core Invariants (NON-NEGOTIABLE)` rules that govern how deep traces are conducted.

## Goal

Produce the evidence package that later stages can trust.

## Execution Rules

- Resolve and record source context if it is missing.
- Use `read-code-workflow` first when the corpus is a code repository.
- Use `read-paper-workflow` first when the corpus is primarily papers, reports, articles, RFCs, or other non-code source documents.
- For a mixed corpus, choose the dominant source family first and capture equivalent depth in the reading note across the rest of the evidence set.
- If one important storyline still has gaps after the normal reading pass, use `wiki-researcher`.
- Keep the reading note scoped to the requested subsystem when the user does not want a repo-wide pass.

## Minimum Output

Before finishing, update `knowledge-base/_meta/01-reading-note.md` with:

1. reading goal and scope,
2. static vs runnable evidence note,
3. module, source, or architecture map,
4. one traced main storyline or evidence path,
5. key data structures,
6. deferred side plots,
7. open questions and confidence,
8. a `## Handoff Status` section that marks the reading pass as complete, partial, or blocked, names the recommended next stage, and records any blocking evidence gaps.

## Handoff

End by using the `## Handoff Status` section to name:

- candidate page groups for Stage 2,
- whether the reading pass is complete, partial, or blocked,
- missing evidence that may affect planning,
- and the recommended next stage.
