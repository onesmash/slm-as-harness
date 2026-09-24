# co-storm-autonomous-research

Autonomous Co-STORM-style research: warm-start stable expert perspectives, collect one grounded result from an independent subagent for each expert in every round, merge any newly retrieved evidence into the shared registry, let the Moderator adjudicate semantic coverage with deterministic guardrails, reorganize the knowledge map, and synthesize a cited complete or explicitly partial report whose body uses compact numeric [n] markers and whose final Evidence index maps each used marker to its exact registry source locator, without user intervention; after bounded self-repair, hard blocks terminate with a partial handoff. NOTE: the warm-start stage seeds the full planned topic set with no numeric ceiling and every seeded topic must be assessed before the report can be complete; set constraints.max_rounds (default 8) and constraints.max_steps (default 36) large enough to cover the planned topics, otherwise the run ends as an explicitly partial report. constraints.coverage_threshold remains only a deterministic lower bound on distinct assessed topics.

Generated from `spec.json` by `workflow-creator`. Treat `spec.json` as the
source of truth; edit it and rerun the creator rather than editing the
generated surfaces by hand.

## Stage path

- `warm_start_shared_space` (main) - routes to `research-nex`
- `launch_expert_subagents` (main) - routes to `research-nex`, `search-nex`
- `autonomous_roundtable` (main) - routes to `research-nex`
- `reorganize_knowledge_space` (main) - routes to `research-nex`
- `synthesize_report` (main) - routes to `report-nex`
- `verify_report` (main) - routes to `report-nex`
- `repair_report` (recovery) - routes to `report-nex`
- `finalize_collaborative_report` (final)

## Dependencies

- `research-nex` (skill, required) - Own autonomous perspective-guided research, grounded expert turns, and knowledge-space maintenance.
- `search-nex` (skill, required) - Provide source discovery and web-search evidence support required by research-nex.
- `report-nex` (skill, required) - Own evidence-grounded report synthesis, report quality review, and citation repair.

## Runtime defaults

- `max_steps`: 36
- `max_rounds`: 8
- `min_evidence_items`: 3
- `coverage_threshold`: 2
- `max_reorganizations`: 3
- `max_report_synthesis_attempts`: 4

## Durable state

- `state_mode`: `custom`

## Related files

- `references/flowchart.md` - rendered graph documentation
- `references/agent-review.md` - review checklist for this workflow
- `prompts/` - one prompt asset per step
- `tests/` - workflow-local regression coverage
