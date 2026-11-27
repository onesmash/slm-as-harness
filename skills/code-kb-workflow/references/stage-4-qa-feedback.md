# Stage 4: QA And Feedback

## Purpose

Test whether the current knowledge base can answer real repo or corpus questions and stay fresh as the code or source set changes.

## Primary Skill Composition

- Use `wiki-qa` for grounded question answering.
- Use `wiki-researcher` when the answer needs deeper tracing than the page already provides.
- Use `wiki-changelog` to detect likely freshness drift from recent commits or source additions.

## Required Outputs

- `knowledge-base/_meta/04-qa-feedback.md`
- `knowledge-base/qa/qa-round-YYYY-MM-DD.md`
- backlog updates in `03-page-backlog.md`

## QA Checklist

- Ask real user-style questions, not only page-title questions.
- Record whether the answer came from the current knowledge base, fresh source analysis, or both.
- Flag stale, thin, or contradictory pages.
- When `knowledge-base/llms.txt` exists, validate link coverage, path correctness, and whether the listed pages still match the current knowledge-base structure.
- For each issue, name the loop-back stage: 1, 2, or 3.

## Recommended Question Types

- architecture: "how does this subsystem work"
- ownership: "which files or modules matter first"
- data flow: "what happens from input to persistence"
- freshness: "which pages are stale after recent commits"
- onboarding: "what should a new contributor read first"
- llms surface: "does `knowledge-base/llms.txt` cover the right pages and point to valid paths"
- synthesis: "what does this source set currently say about X"
