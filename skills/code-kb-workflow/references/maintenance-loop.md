# Maintenance Loop

Use this workflow as a repeatable system, not a one-time documentation sprint.

## Common Modes

| Situation | Recommended path |
|----------|------------------|
| New repo or source corpus with no docs | `1 -> 2 -> 3 -> 4` |
| Existing docs but weak structure | `2 -> 3 -> 4` |
| User asks to restart from understanding but a reading note already exists | clarify reread vs continue from Stage 2 |
| Onboarding or changelog request with only a reading note | `2 -> 3` |
| New subsystem or source batch landed this week | `1 (partial) -> 2 (partial) -> 3 -> 4` |
| Mixed request to reread one area and refresh another | partial maintenance path, usually `1 (partial) -> 2 (partial) -> 3 -> 4` |
| Docs feel stale after recent commits or source ingests | `4 -> 2 or 3` |
| Users ask questions the KB cannot answer well | `4 -> 1 or 3` |

Restart phrases do not override existing durable artifacts. When Stage 1 outputs already exist, confirm whether the user wants a true reread or a continuation path.

## Freshness Policy

- Use `wiki-changelog` before major refreshes.
- Compare recent code areas or source additions against the current page backlog.
- Refresh only the impacted pages unless the structure itself is broken.
- Regenerate or validate `knowledge-base/llms.txt` after page-hierarchy changes or when high-value pages are added, renamed, or retired.

## Optimization Policy

- If Stage 4 repeatedly flags the same weak area, strengthen Stage 1 evidence capture for that subsystem.
- If Stage 3 keeps producing overlapping pages, fix Stage 2 page boundaries instead of writing more prose.
- If onboarding pages drift from architecture pages, regenerate or reconcile onboarding in Stage 3 before adding new QA layers.

## Maintenance Log Format

Append to `knowledge-base/_meta/maintenance-log.md`:

```md
## 2026-04-03
- Trigger: QA round found stale auth pages after recent commit summary.
- Action: reran Stage 2 for auth subtree, Stage 3 for auth pages.
- Result: backlog reduced from 5 stale pages to 1 open item.
```
