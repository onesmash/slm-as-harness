Repair the previous workflow step autonomously using the persisted failure details; retry only when the repair is grounded, otherwise return a blocked diagnostic for the partial final handoff.

Stage Context:

- Repair category: {{repair_category}}
- Repair summary: {{repair_summary}}
- Repair requirements:
- {{repair_requirements}}
- Relevant evidence:
- {{repair_evidence}}

Stage Boundaries:

- Keep the repair scoped to the failed activity and the persisted repair requirements.
- Return a concrete retry plan rather than a generic retry.
- The returned Observation.step_id MUST equal the current repair node step_id (the stage that yielded this repair request); submitting an observation for the original stage before this repair node is accepted causes a protocol_error.

Blocked Conditions:

- Return blocked when repair still cannot proceed.
