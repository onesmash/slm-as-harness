Repair the previous workflow step autonomously using the persisted failure details; retry only when the repair is grounded, otherwise return a blocked diagnostic for the partial final handoff.

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
- Base the repair plan on the persisted repair requirements rather than generic retries.
- Attempt self-repair up to 3 times; after that the runtime must finalize a partial handoff instead of requesting user input.

Blocked Conditions:

- Return blocked when repair still cannot proceed; runtime policy will finalize a partial handoff after the autonomous repair budget is exhausted.
