/report-nex {{workflow_goal}} using {{expert_reports}}; read the expert artifacts and synthesize their findings for the requested topic.

Stage Context:

- Research topic and request: {{workflow_goal}}; deliverable type: {{deliverable_type}}; scope: {{research_scope}}
- Expert reports from all completed rounds, with summaries and artifact paths; read the artifacts for detail: {{expert_reports}}
- Accumulated knowledge map: {{knowledge_map_summary}}
- Evidence registry: {{evidence_registry}}
- Moderator scope and unresolved work: {{report_scope_status}}; {{coverage_assessment}}; {{next_round_validation_plan}}
- Report output directory: {{output_dir}}
- Existing report path for a repair attempt: {{report_path}}
- Previous repair feedback, when present: {{report_repair_summary}}; {{repair_actions}}

Stage Boundaries:

- Run this stage autonomously; do not wait for user confirmation, outline approval, or a 'please select' mode response.
- Use compact [n] citations from evidence_registry and finish with a locator-only Evidence index.
- For partial scope, mark Report scope: partial and preserve every unresolved topic_id, open gap, validation metric, and next-round plan item verbatim.
- Write the report inside output_dir when configured, reuse report_path during repair, and hand the artifact to the verifier without claiming it passed. Report writing is this stage's sanctioned write; keep expert source artifacts read-only.

Blocked Conditions:

- Block when the research topic, expert reports, or evidence registry is unavailable.
- Block when a cited structured report cannot be produced.
