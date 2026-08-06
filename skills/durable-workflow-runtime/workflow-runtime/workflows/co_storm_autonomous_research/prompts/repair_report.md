/content-research-writer {{workflow_goal}} using {{report_path}}, {{quality_findings}}, {{citation_coverage_summary}}, and {{evidence_registry}}; repair the cited report's groundedness, section coverage, or duplication defects and return a handoff for re-synthesis.

Stage Context:

- Report path: {{report_path}}
- Quality findings: {{quality_findings}}
- Citation coverage summary: {{citation_coverage_summary}}
- Evidence registry: {{evidence_registry}}
- Knowledge-map summary: {{knowledge_map_summary}}

Stage Boundaries:

- Keep repairs limited to the report artifact and its evidence grounding; do not invent new research outside the shared evidence registry.
- Do not choose the next workflow node; recovery policy returns to report synthesis.
- Name every repair action that the next synthesis pass must apply.

Blocked Conditions:

- Block when a concrete repair action cannot be derived from the persisted quality findings.
- Block when the report or evidence registry is unavailable.
