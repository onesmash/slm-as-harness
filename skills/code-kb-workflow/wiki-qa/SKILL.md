---
name: wiki-qa
description: Answers questions about a code repository or source corpus using grounded source analysis. Use when the user asks a question about how something works, wants to understand a component or topic, or needs help navigating the knowledge base.
license: MIT
metadata:
  author: Microsoft
  version: "1.0.0"
---

# Wiki Q&A

Answer repository or corpus questions grounded entirely in source evidence.

## When to Activate

- User asks a question about the codebase or source set
- User wants to understand a specific file, function, or component
- User asks "how does X work" or "where is Y defined"
- User asks what a source set currently says about a topic

## Source Context Resolution (MUST DO FIRST)

Before answering any question, you MUST determine the source context:

1. **Check for git remote or canonical source URL**
2. **Ask the user**: _"Is this local-only, or do you have a canonical source URL (repository, shared docs site, or similar)?"_
   - Canonical URL provided → use **linked citations** when stable links are possible
   - Local-only → use **local citations**: `(file_path:line_number)`
3. **Determine default branch** only when linked repository citations are needed
4. **Do NOT proceed** until source context is resolved

## Procedure

1. Resolve source context (see above)
2. Detect the language of the question; respond in the same language
3. Search the codebase or source set for relevant files
4. Read those files or source documents to gather evidence
5. Synthesize an answer with inline linked citations

## Response Format

- Use `##` headings, code blocks with language tags, tables, bullet lists
- Cite sources inline using resolved format:
  - **Remote**: `[src/path/file.ts:42](REPO_URL/blob/BRANCH/src/path/file.ts#L42)`
  - **Local**: `(src/path/file.ts:42)`
- Include a "Key Files or Sources" table mapping artifacts to their roles (with linked citations in the first column)
- **Include at least 1 Mermaid diagram** when the answer involves architecture, data flow, or relationships — a diagram makes the answer 10x more useful
- **Use tables** for any structured data in the answer (component lists, API endpoints, config options, comparisons)
- If information is insufficient, say so and suggest files to examine

## Rules

- ONLY use information from actual source files or source documents
- NEVER invent, guess, or use external knowledge
- Think step by step before answering
