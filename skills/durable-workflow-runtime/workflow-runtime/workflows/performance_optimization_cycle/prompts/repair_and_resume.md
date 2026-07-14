/systematic-debugging investigate the persisted verification failure for {{return_stage_id}} using {{repair_summary}} and {{repair_evidence}}; identify the root cause before defining repair actions for a retry.

Stage Context:

- Current step: {{current_step_id}}
- Return stage: {{return_stage_id}}
- Source stage: {{source_stage_id}}
- Repair category: {{repair_category}}
- Repair summary: {{repair_summary}}
- Repair requirements:
- {{repair_requirements}}
- Relevant evidence:
- {{repair_evidence}}

Stage Boundaries:

- Keep the retry scoped to the original return stage instead of changing workflow routing.
- Do not implement a fix until the root cause and the evidence supporting it are recorded.
- For blocked work, record the blocker and begin a new cycle rather than requesting user input.

Blocked Conditions:

- Return blocked when the evidence needed for root-cause investigation is unavailable; runtime will record the blocker and begin a new cycle.
