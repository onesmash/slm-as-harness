/content-research-writer {{workflow_goal}} using {{report_path}}, {{report_summary}}, {{report_sections}}, {{evidence_registry}}, and {{coverage_map}}; independently verify section coverage, citation referential integrity, unsupported claims, duplication, and coherence, then return a structured pass or repair verdict without changing workflow routing.

Stage Context:

- Report path: {{report_path}}
- Report summary: {{report_summary}}
- Report sections: {{report_sections}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Knowledge-map summary: {{knowledge_map_summary}}

Stage Boundaries:

- Do not silently rewrite the report while performing verification; return concrete findings for the repair stage.
- Treat unknown citation identifiers, missing section coverage, and unsupported substantive claims as failures.
- A pass requires a report artifact, traceable citations, and no unresolved critical quality findings.
- Do not choose the repair or final node; runtime policy owns the transition.

Blocked Conditions:

- Block when the report path, evidence registry, or report sections are unavailable.
- Block when the report cannot be read for citation and section verification.
