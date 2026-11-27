# Artifact Contract

The workflow stores durable state in `knowledge-base/_meta/` and published documents in `knowledge-base/`. In bootstrap or non-code corpus scenarios it also maintains adjacent control artifacts such as `raw/`, `AGENTS.md`, `knowledge-base/index.md`, `knowledge-base/log.md`, and `knowledge-base/llms.txt`.

## Default Layout

```text
AGENTS.md
raw/
  sources/
knowledge-base/
  README.md
  index.md
  log.md
  llms.txt
  architecture/
  components/
  onboarding/
  changelog/
  qa/
  _meta/
    source-context.md
    01-reading-note.md
    02-catalogue-plan.md
    03-page-backlog.md
    04-qa-feedback.md
    maintenance-log.md
```

## Required Stage Inputs And Outputs

| Stage | Must read first | Must write before finishing |
|------|------------------|-----------------------------|
| 1 | source corpus plus `source-context.md` when available | `01-reading-note.md` with a `## Handoff Status` section |
| 2 | `01-reading-note.md` if present | `02-catalogue-plan.md` with the required section schema including `## LLM Surface Coverage`, `03-page-backlog.md`, and an explicit repo-root `AGENTS.md` bootstrap decision |
| 3 | `02-catalogue-plan.md`, `03-page-backlog.md`, plus `wiki-page-writer/SKILL.md` for the per-page format contract | at least one *real* page (a real page satisfies "any published page under `knowledge-base/`" in `## Minimum Content Requirements` below — prose-and-citations alone is half the contract) or a materially-refreshed planned LLM-readable surface, plus backlog status updates, plus any required index/log/llms refresh and root `AGENTS.md` creation when bootstrap rules or the plan require it. A page that fails the format contract stays `planned` in the backlog, not `drafted`. |
| 4 | existing `knowledge-base/` pages, `03-page-backlog.md`, and `wiki-page-writer/SKILL.md` for the format rubric | `04-qa-feedback.md` (with a `## Format compliance` section reporting `scripts/check_page_format.py` results), one QA artifact under `qa/`, and backlog updates |

## Routing-Relevant Artifact Signals

Use these artifact signals when the orchestrator needs to choose the smallest valid path:

- No `knowledge-base/` and no `01-reading-note.md` means the corpus is still at Stage 1.
- `01-reading-note.md` exists but `02-catalogue-plan.md` or `03-page-backlog.md` is missing, weak, empty, or stale means Stage 2 should refresh planning state.
- `02-catalogue-plan.md` and `03-page-backlog.md` both exist means Stage 3 prerequisites are satisfied for page writing, onboarding, and changelog requests.
- `02-catalogue-plan.md` and `03-page-backlog.md` both exist also means Stage 3 prerequisites are satisfied for planned `llms.txt` requests.
- Existing written pages plus a correctness, staleness, or completeness question means Stage 4.
- A restart-from-understanding request is not enough to rerun Stage 1 when `01-reading-note.md` already exists; clarify whether the user wants a reread or a continuation path.

## Common Adjacent Control Artifacts

| Artifact | Why it matters |
|------|----------------|
| `AGENTS.md` or equivalent schema file | Encodes how the knowledge base should be maintained |
| `raw/` | Keeps immutable source evidence separate from synthesized pages |
| `knowledge-base/index.md` | Gives the agent a stable first lookup surface |
| `knowledge-base/log.md` | Preserves a chronological activity trail |

For bootstrap runs, `AGENTS.md` is mandatory, not optional.

## Minimum Content Requirements

### 01-reading-note.md

- reading goal and scope
- static vs runnable evidence note
- one main storyline traced end to end
- key modules and data structures
- deferred side plots
- open questions
- `## Handoff Status` with reading-pass state (`complete`, `partial`, or `blocked`), recommended next stage, and blocking evidence gaps

### 02-catalogue-plan.md

- `## Page Hierarchy` - target page tree
- `## Writing Order` - dependencies-first writing order for Stage 3
- `## Evidence Sets` - page-level evidence sources
- `## Onboarding Coverage` - onboarding coverage plan
- `## Changelog Coverage` - changelog coverage plan
- `## LLM Surface Coverage` - whether `knowledge-base/llms.txt` is needed, and how Stage 3 should handle it
- `## Bootstrap Decision` - whether repo-root `AGENTS.md` already exists and, if not, the concrete Stage 3 action to create or refresh it

### 03-page-backlog.md

Use a flat table:

| Page | Status | Source stage | Evidence set | Next action |
|------|--------|--------------|--------------|-------------|

### 04-qa-feedback.md

- tested questions
- grounded answers or failure notes
- stale or weak pages
- a `## Format compliance` section reporting per-page output of `scripts/check_page_format.py` (which checks frontmatter, Mermaid quotas, source comments after diagrams, and the `## Related Pages` table). Pages with violations loop back to Stage 3.
- recommended loop-back stage for each issue

### any published page under `knowledge-base/`

A markdown file under `knowledge-base/` is *not* a real page until all of the following hold. The source of truth is [`wiki-page-writer/SKILL.md`](../wiki-page-writer/SKILL.md) and [`wiki-page-writer/references/acceptance-criteria.md`](../wiki-page-writer/references/acceptance-criteria.md); this list is the contract-level summary so Stage 3 and Stage 4 cannot proceed by accident with format-incomplete pages.

- **VitePress frontmatter** at the top of the file:
  ```
  ---
  title: "Page title"
  description: "One-line description"
  ---
  ```
- **Mermaid diagrams**:
  - minimum **3** for a small page, **4** for a medium page, **5+** for a large page (scope is judged by the writer, but the linter enforces ≥3),
  - mixing **at least 2** of `graph` / `sequenceDiagram` / `classDiagram` / `stateDiagram-v2` / `erDiagram` / `flowchart`,
  - every `sequenceDiagram` block uses `autonumber`,
  - dark-mode color overrides per `wiki-page-writer/SKILL.md` ("MANDATORY" colors).
- A `<!-- Sources: file:line, file:line -->` comment block immediately after every Mermaid diagram, naming the source files the diagram is derived from.
- **Citations**: every non-trivial claim has a `file_path:line` citation. Listing tables (APIs, configs, components, comparisons) include a `Source` column with linked citations.
- **Cross-references**: a `## Related Pages` section at the end, formatted as a table with at minimum `Page` and `Relationship` columns. Bullet lists do not satisfy this rule.
- **VitePress compatibility**: bare generics outside code fences are escaped (`` `List<T>` `` not bare `List<T>`); no `<br/>` in Mermaid blocks; all hex colors are 3 or 6 digits.

The exceptions:

- `knowledge-base/llms.txt` follows the [llms.txt spec](https://llmstxt.org); it is plain text and does not require frontmatter, Mermaid, or `## Related Pages`.
- `knowledge-base/_meta/*` files are workflow state, not published pages, and are governed by the per-file rules above (`01-reading-note.md`, `02-catalogue-plan.md`, `03-page-backlog.md`, `04-qa-feedback.md`).
- `knowledge-base/log.md` is an append-only activity log; one or more diagrams are nice-to-have but not required.
- `knowledge-base/index.md` is a table of contents; if the linter is strict about Mermaid quotas on it, downgrade to "warn, not fail" rather than block the run.

## Update Policy

- Update in place when artifacts already exist.
- Preserve evidence and previous decisions instead of replacing them with a thinner version.
- When a page is intentionally retired, record that in `maintenance-log.md`.
- Preserve source provenance and keep adjacent control artifacts synchronized when the page set changes materially.
- Keep `knowledge-base/llms.txt` synchronized with the current published page set whenever it is in scope.
- Never treat `AGENTS.md` as optional during a bootstrap run. If it is missing, Stage 2 must plan it and Stage 3 must create it.
