# Managed AGENTS Block Template

When bootstrapping or refreshing repo-root `AGENTS.md`, write one managed block with this shape. Start from this template, then customize only the repo-specific details that truly differ.

```md
<!-- code-kb:start -->
# Code KB Workflow

Use `code-kb-workflow` whenever the user wants to build, refresh, or validate a durable `knowledge-base/` for this repository. The default output lives in `knowledge-base/`, and workflow state should be stored in `knowledge-base/_meta/`.

## Always Do

- Use `code-kb-workflow` as the entrypoint when the request is about repo wiki generation, source-grounded documentation, onboarding guides, changelog-backed refreshes, or QA for an existing `knowledge-base/`.
- Treat `knowledge-base/llms.txt` as an LLM-facing discovery surface for this knowledge base. It is a navigation aid, not a replacement for `AGENTS.md`.
- When the user asks repo-understanding questions, wants a reading path, or asks where relevant knowledge-base pages live, consult `./knowledge-base/llms.txt` early to identify the right pages before broader searching.
- Route to the smallest stage that matches the user's request unless they explicitly ask for the full workflow.
- Leave behind durable artifacts for the next stage. If the user asks to run the workflow, do not stop at verbal guidance only.
- Treat `knowledge-base/_meta/03-page-backlog.md` as the durable queue for pages to create, refresh, or retire.
- Treat `knowledge-base/_meta/04-qa-feedback.md` as the source of truth for follow-up work that should loop back into reading, planning, or writing.

## First Move

Before routing the request, resolve:

1. What repository or source corpus is in scope.
2. Whether the source of truth is local-only or has a canonical remote/source URL.
3. Whether the user wants the full four-stage workflow or only one stage.

## Stage Routing

| Situation | Run | Main output |
|-----------|-----|-------------|
| No `knowledge-base/` exists yet, or the user wants to start by understanding the code/source material | `code-kb-stage-1-read-code` | `knowledge-base/_meta/01-reading-note.md` |
| A reading note exists, but page structure or backlog is missing or weak | `code-kb-stage-2-plan` | `knowledge-base/_meta/02-catalogue-plan.md`, `knowledge-base/_meta/03-page-backlog.md` |
| A plan/backlog exists and the user wants pages written or refreshed | `code-kb-stage-3-write` | Pages under `knowledge-base/` plus backlog updates |
| Pages exist and the user asks whether the knowledge base is correct, stale, or complete | `code-kb-stage-4-qa` | `knowledge-base/_meta/04-qa-feedback.md`, `knowledge-base/qa/` |
| The user asks for the entire workflow | `1 -> 2 -> 3 -> 4` | Full `knowledge-base/` maintenance loop |

## Long-Term Maintenance

- Do not rewrite the whole `knowledge-base/` by default when only one subsystem changed.
- Use `wiki-changelog` to narrow the refresh scope before planning or QA whenever recent commits matter.
- Preserve stage artifacts unless the user explicitly asks to regenerate them.
- Keep `knowledge-base/llms.txt` aligned with the current published page set whenever page hierarchy, titles, or major topic coverage changes.
- During bootstrap, treat `raw/`, `AGENTS.md`, `knowledge-base/index.md`, and `knowledge-base/log.md` as first-class control artifacts.
- A bootstrap run is not complete until the repository has a root `AGENTS.md` or equivalent maintenance instructions for future agents.

## When Not To Use

- Do not force `code-kb-workflow` for one-off prose docs that are not grounded in a source corpus.
- Do not use it for pure code questions, pure PR review, or general research tasks that do not need durable `knowledge-base/` artifacts.
- In those cases, route directly to the narrower skill that fits the task.

## Skills Quick Reference

| Task | Read this skill file |
|------|----------------------|
| Route or run the overall documentation workflow | `code-kb-workflow/SKILL.md` |
| Read code and create the stage-1 note | `code-kb-workflow/stage-1-read-code/SKILL.md` |
| Plan the documentation structure and backlog | `code-kb-workflow/stage-2-plan/SKILL.md` |
| Write or refresh `knowledge-base/` pages | `.code-kb-workflow/stage-3-write/SKILL.md` |
| QA the knowledge base and generate feedback | `code-kb-workflow/stage-4-qa/SKILL.md` |

<!-- code-kb:end -->
```

Keep the managed block focused on the maintenance contract. Put only the `code-kb` workflow guidance inside these markers. Leave unrelated agent instructions outside the managed block so future refreshes can update only this section safely.
