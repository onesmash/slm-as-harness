# Stage 2: Knowledge-Base Writing Plan

## Purpose

Turn source evidence into a writing system instead of a one-off outline.

## Primary Skill Composition

- Use `wiki-architect` to build the catalogue.
- Use `wiki-onboarding` to reserve onboarding deliverables.
- Use `wiki-changelog` when recent commit history or source-ingestion history should influence scope or freshness.
- Reserve `knowledge-base/llms.txt` when the user wants an LLM-readable discovery surface for the current knowledge base.

## Required Outputs

- `knowledge-base/_meta/02-catalogue-plan.md`
- `knowledge-base/_meta/03-page-backlog.md`
- an explicit bootstrap decision for repo-root `AGENTS.md`

## Required Section Schema

- `## Page Hierarchy` - target directory tree for `knowledge-base/`
- `## Writing Order` - dependencies-first page sequence for Stage 3
- `## Evidence Sets` - page-level evidence sources and source mappings
- `## Onboarding Coverage` - whether onboarding outputs are needed and for which roles
- `## Changelog Coverage` - whether changelog outputs are needed and what freshness window matters
- `## LLM Surface Coverage` - whether `knowledge-base/llms.txt` is needed
- `## Bootstrap Decision` - whether Stage 3 must create or refresh repo-root `AGENTS.md`, the target control file, and the concrete Stage 3 action or explicit no-op rationale

## Plan Checklist

- pages grouped by architecture, components, operations, onboarding, and changelog
- freshness or update scope when recent commits matter
- whether `knowledge-base/llms.txt` is needed, and what it should cover
- control artifacts to bootstrap or refresh when the corpus needs them
- whether repo-root `AGENTS.md` exists, and if missing, a concrete Stage 3 action to create it

## Long-Term Design Rules

- Prefer stable page names tied to subsystems, not temporary initiatives.
- Separate evergreen pages from time-scoped changelog pages.
- Keep onboarding, architecture, and changelog as first-class sections.
- Treat `knowledge-base/llms.txt` as a derived discovery artifact tied to the published page set, not as a substitute for the underlying pages.
- Convert open questions into backlog items instead of hiding them in prose.
- Reserve `index.md`, `log.md`, and a schema file such as `AGENTS.md` when the corpus is being bootstrapped from raw evidence rather than an existing repo wiki.
- Treat root `AGENTS.md` as mandatory for bootstrap runs, not as a nice-to-have.
