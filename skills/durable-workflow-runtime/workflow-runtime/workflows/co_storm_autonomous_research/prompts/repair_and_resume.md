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

Blocked Conditions:

- Return blocked when repair still cannot proceed.
