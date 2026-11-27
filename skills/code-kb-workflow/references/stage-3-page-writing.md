# Stage 3: Knowledge-Base Page Writing

## Purpose

Generate or refresh the actual Markdown pages under `knowledge-base/`.

## Primary Skill Composition

- Use `wiki-page-writer` for normal technical pages or other source-grounded pages.
- Use `wiki-onboarding` for onboarding guides.
- Use `wiki-changelog` for changelog or recent-change pages.
- Use `wiki-llms-txt` for `knowledge-base/llms.txt` when an LLM-readable discovery surface is in scope.

## Required Output Rules

- Every substantive page must be grounded in source evidence. When documenting code, that evidence should come from code.
- Use the citation style resolved in `source-context.md`.
- Prefer updating existing pages in place before creating new duplicates.
- Keep `03-page-backlog.md` synchronized with what was written or deferred.
- Refresh control artifacts such as `knowledge-base/index.md`, `knowledge-base/log.md`, or `AGENTS.md` when the page set or operating contract changes materially.
- Refresh `knowledge-base/llms.txt` when the plan calls for LLM-readable delivery or when the page hierarchy changes materially.
- Do not create `knowledge-base/llms-full.txt` or repo-root `llms.txt` from this workflow.
- For bootstrap runs, root `AGENTS.md` is mandatory. If it is missing, Stage 3 must create it.

## Page Families

- `knowledge-base/README.md`
- `knowledge-base/index.md`
- `knowledge-base/log.md`
- `knowledge-base/llms.txt`
- `knowledge-base/architecture/`
- `knowledge-base/components/`
- `knowledge-base/onboarding/`
- `knowledge-base/changelog/`

## Finish Criteria

Stage 3 is not complete until at least one of these is true:

- a new page was written,
- an existing page was materially refreshed,
- a planned LLM-readable surface was materially refreshed,
- or the backlog was reduced with evidence-backed status notes.

For bootstrap runs, this finish criterion applies only after root `AGENTS.md` exists.
