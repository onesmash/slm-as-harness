/content-research-writer {{workflow_goal}} using {{report_path}}, {{repair_summary}}, {{repair_requirements}}, {{repair_evidence}}, and {{evidence_registry}}; translate audit findings into concrete repair actions and a handoff for the next synthesize_report pass without rewriting the report body in this stage.

Stage Context:

- Report path: {{report_path}}
- Verifier or recovery context from persisted repair state: {{repair_summary}}
- Repair requirements from persisted repair state: {{repair_requirements}}
- Repair evidence from persisted repair state: {{repair_evidence}}
- Evidence registry: {{evidence_registry}}
- Knowledge-map summary: {{knowledge_map_summary}}

Stage Boundaries:

- Keep repairs limited to the report artifact and its evidence grounding; do not invent new research outside the shared evidence registry.
- Return concrete repair actions and a handoff for the next report pass.
- Name every repair action that the next synthesis pass must apply.

Blocked Conditions:

- Block when a concrete repair action cannot be derived from the available audit or repair context.
- Block when the report or evidence registry is unavailable.
