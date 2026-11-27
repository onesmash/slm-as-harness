# Source Context

Stages 2 to 4 depend on the source-context rules used by `wiki-architect`, `wiki-page-writer`, `wiki-onboarding`, `wiki-changelog`, `wiki-llms-txt`, `wiki-qa`, and `wiki-researcher`.

## Required Resolution Steps

1. Check whether the corpus is a git repository with a remote URL, or whether it has another canonical source URL.
2. Ask whether the corpus should be treated as local-only or tied to a canonical source URL.
3. Determine the working branch only when linked repository citations are needed.
4. Record the answer in `knowledge-base/_meta/source-context.md`.

## Minimal Recorded Format

```md
# Source Context
- Corpus root: /abs/path/to/corpus
- Corpus type: code-repository | document-corpus | mixed
- Repository mode: local-only | linked
- Remote or canonical source URL: https://example.com/org/repo
- Working branch: main | n/a
- Citation style: local | linked
- Primary source set: src/ | raw/ | docs/
```

## Why This Exists

- Stage 1 can often proceed with local evidence only.
- Stages 2 to 4 need stable citation rules so generated pages do not drift between local and remote link styles.
- A durable `source-context.md` prevents repeated prompts in long maintenance cycles.
- This works for code repositories, document corpora, and mixed evidence sets as long as the citation contract is explicit.
