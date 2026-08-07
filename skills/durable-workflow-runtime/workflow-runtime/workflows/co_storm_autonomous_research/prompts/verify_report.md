/content-research-writer {{workflow_goal}} using {{report_path}}, {{report_summary}}, {{report_sections}}, {{evidence_registry}}, and {{coverage_map}}; independently verify section coverage, citation referential integrity, unsupported claims, duplication, and coherence, then return a structured pass or repair verdict.

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
- Return concrete findings and a pass or repair verdict without rewriting the report.

Blocked Conditions:

- Block when the report artifact, evidence registry, or report sections are unavailable.
- Block when the report or evidence cannot be checked for citation and section coverage.
