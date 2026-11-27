---
name: wiki-llms-txt
description: Generates `knowledge-base/llms.txt` for LLM-friendly project documentation following the llms.txt specification. Use when the user wants to create an LLM-readable summary, generate `llms.txt`, or make a `knowledge-base/` wiki accessible to language models without producing repo-root `llms.txt` or `llms-full.txt`.
license: MIT
metadata:
  author: Microsoft
  version: "1.0.0"
---

# llms.txt Generator

Generate `knowledge-base/llms.txt` that provides LLM-friendly access to a published `knowledge-base/` or similar wiki documentation set, following the [llms.txt specification](https://llmstxt.org/).

## When This Skill Activates

- User asks to generate `llms.txt` or mentions the llms.txt standard
- User wants to make documentation "LLM-friendly" or "LLM-readable"
- User asks for a project summary file for language models
- User wants a knowledge-base discovery surface but does not need a fully inlined export

## Source Repository Resolution (MUST DO FIRST)

Before generating, resolve the source repository context:

1. **Check for git remote**: Run `git remote get-url origin`
2. **Ask the user**: _"Is this a local-only repository, or do you have a source repository URL?"_
   - Remote URL → store as `REPO_URL`
   - Local → use relative paths only
3. **Determine default branch**: Run `git rev-parse --abbrev-ref HEAD`
4. **Do NOT proceed** until resolved

## llms.txt Format (Spec-Compliant)

The file follows the [llms.txt specification](https://llmstxt.org/):

```markdown
# {Project Name}

> {Dense one-paragraph summary — what it does, who it's for, key technologies}

{Important context paragraphs — constraints, architectural philosophy, non-obvious things}

## {Section Name}

- [{Page Title}]({relative-path-to-md}): {One-sentence description of what the reader will learn}

## Optional

- [{Page Title}]({relative-path-to-md}): {Description — these can be skipped for shorter context}
```

### Key Rules

1. **H1** — Project name (exactly one, required)
2. **Blockquote** — Dense, specific summary (required). Must be unique to THIS project.
3. **Context paragraphs** — Non-obvious constraints, things LLMs would get wrong without being told
4. **H2 sections** — Organized by topic, each with a list of `[Title](url): Description` entries
5. **"Optional" H2** — Special meaning: links here can be skipped for shorter context
6. **Relative links** — `knowledge-base/llms.txt` must use knowledge-base-relative paths such as `./architecture/overview.md`
7. **Dynamic** — ALL content derived from actual published pages, not templates
8. **Section order** — Most important first: Onboarding → Architecture → Getting Started → Deep Dive → Optional

### Description Quality

| ❌ Bad | ✅ Good |
|--------|---------|
| "Architecture overview" | "System architecture showing how Orleans grains communicate via message passing with at-least-once delivery" |
| "Getting started guide" | "Prerequisites, local dev setup with Docker Compose, and first API call walkthrough" |
| "The API reference" | "REST endpoints with auth requirements, rate limits, and request/response schemas" |

## Prerequisites

This skill works best when `knowledge-base/` pages already exist (for example after Stage 3 of `code-kb-workflow` or an equivalent wiki-writing pass). If no knowledge base exists yet:

1. Suggest running the earlier knowledge-base stages first so there are real pages to summarize
2. OR generate a minimal `knowledge-base/llms.txt` from README + source code scan when the user explicitly wants an early discovery surface

## Output Files

Generate one file:

| File | Purpose | Discoverability |
|------|---------|-----------------|
| `knowledge-base/llms.txt` | Knowledge-base-relative links | For knowledge-base navigation and agent discovery rooted in the published docs tree. |

Do not create `knowledge-base/llms-full.txt` or repo-root `llms.txt` as part of this workflow.

## Validation Checklist

Before finalizing:

- [ ] All linked files in `knowledge-base/llms.txt` actually exist
- [ ] Blockquote is specific to this project (not generic boilerplate)
- [ ] Sections ordered by importance
- [ ] No duplicate page entries across sections
- [ ] "Optional" section only contains truly optional content
- [ ] `llms.txt` is concise (1-5 KB)
