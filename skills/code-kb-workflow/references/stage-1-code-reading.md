# Stage 1: Source Reading And Understanding

## Purpose

Produce the durable evidence package the rest of the workflow depends on.

## Primary Skill Composition

- Use `read-code-workflow` first for code repositories.
- Use `read-paper-workflow` first for papers, articles, reports, whitepapers, RFCs, and other non-code source documents.
- For mixed corpora, choose the dominant source family first and preserve equivalent evidence depth across the rest of the corpus.
- Add `wiki-researcher` only when one storyline spans too many files for a normal reading pass.

## Output Checklist

- `knowledge-base/_meta/01-reading-note.md`
- scope and source context
- module, source, or concept map
- one traced execution path or evidence storyline
- key data structures
- open questions and confidence
- `## Handoff Status` with pass state (`complete`, `partial`, or `blocked`), recommended next stage, and blocking evidence gaps

## Downscope Rules

- Large repo or corpus: one entrypoint or seed source, three to seven key modules or source clusters, one representative path.
- Missing runtime: explicitly mark the reading note as static-only.
- User asks for one subsystem or topic: keep the note scoped to that area and list untouched areas.

## Handoff To Stage 2

End with a `## Handoff Status` section that records:

1. whether the reading pass is `complete`, `partial`, or `blocked`,
2. candidate page groups and page priority order,
3. terms or source families that need onboarding explanations,
4. blocking evidence gaps or open questions that may require `wiki-researcher`,
5. the recommended next stage.
