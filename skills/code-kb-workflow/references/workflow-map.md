# Workflow Map

This skill family turns source understanding into a maintainable `knowledge-base/`.

## Stage Sequence

```text
Stage 1: Read code and capture evidence
  -> Stage 2: Plan the documentation surface and backlog
    -> Stage 3: Write or refresh pages
      -> Stage 4: QA the published knowledge base and feed gaps back
```

## Stage Responsibilities

### Stage 1

- Primary skill: `read-code-workflow`
- Escalation skill: `wiki-researcher`
- Goal: produce a grounded reading artifact instead of vague understanding
- Deliverable: `knowledge-base/_meta/01-reading-note.md` with `## Handoff Status`

### Stage 2

- Primary skill: `wiki-architect`
- Support skills: `wiki-onboarding`, `wiki-changelog`
- Goal: turn source understanding into a documentation catalogue and update backlog
- Deliverables:
  - `knowledge-base/_meta/02-catalogue-plan.md` with the required section schema, `## LLM Surface Coverage`, and `## Bootstrap Decision`
  - `knowledge-base/_meta/03-page-backlog.md`

### Stage 3

- Primary skill: `wiki-page-writer`
- Support skills: `wiki-onboarding`, `wiki-changelog`, `wiki-llms-txt`
- Goal: turn planned pages into real Markdown in `knowledge-base/`
- Deliverables:
  - section pages under `knowledge-base/`
  - onboarding pages under `knowledge-base/onboarding/`
  - changelog pages under `knowledge-base/changelog/`
  - `knowledge-base/llms.txt`

### Stage 4

- Primary skill: `wiki-qa`
- Support skills: `wiki-researcher`, `wiki-changelog`
- Goal: answer source-grounded questions against the current knowledge base, detect evidence gaps, and create a repair loop
- Deliverables:
  - `knowledge-base/_meta/04-qa-feedback.md`
  - `knowledge-base/qa/qa-round-YYYY-MM-DD.md`
  - backlog updates for stages 1 to 3

## Independent Run Rules

- A stage may run alone if its required input artifact already exists or the user supplies equivalent scope directly.
- Stage 2 can run without Stage 1 only when the repo or source corpus is small and the user explicitly wants a lightweight catalogue pass.
- Stage 3 can run without Stage 2 only for a named page or a tiny repo or corpus.
- Stage 4 can run at any time, but should say when confidence is lower because earlier stage artifacts are missing.
