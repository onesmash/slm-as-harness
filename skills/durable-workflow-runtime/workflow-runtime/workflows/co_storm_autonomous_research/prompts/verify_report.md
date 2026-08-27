/content-research-writer {{workflow_goal}} using {{report_path}}, {{report_summary}}, {{report_sections}}, {{evidence_registry}}, {{coverage_map}}, {{coverage_assessment}}, {{next_round_validation_plan}}, and {{report_scope_status}}; independently verify section coverage, citation referential integrity, in-place source locators beside each [n], unsupported claims, duplication, coherence, and faithful disclosure of the Moderator's complete-or-partial scope decision, then return a structured pass or repair verdict.

Stage Context:

- Report path: {{report_path}}
- Report summary: {{report_summary}}
- Report sections: {{report_sections}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Moderator semantic coverage assessment: {{coverage_assessment}}
- Outstanding next-round validation plan: {{next_round_validation_plan}}
- Report scope status: {{report_scope_status}}
- Moderator coverage-sufficient flag: {{coverage_sufficient}}
- Knowledge-map summary: {{knowledge_map_summary}}

Stage Boundaries:

- Do not silently rewrite the report while performing verification; return concrete findings for the repair stage.
- Treat unknown citation identifiers, including numbers absent from the merged evidence_registry, missing section coverage, and unsupported substantive claims as failures.
- Treat number-only [n] citations as a citation failure when the matching evidence_registry locator is missing from nearby report text.
- A failed report verifier must still persist fail-closed audit fields (quality_verdict=repair, report_ready=false, findings including the verifier message) so repair_report can see them.
- A pass requires a report artifact, traceable citations, and no unresolved critical quality findings.
- A partial report may pass only when it contains the exact `Report scope: partial` marker and faithfully lists every unresolved topic id, open gap, validation metric, and next-round plan item; reject any partial report that presents itself as complete.
- A complete report may pass only when coverage_sufficient is true, next_round_validation_plan is empty, and the report contains the exact `Report scope: complete` marker.
- Return concrete findings and a pass or repair verdict without rewriting the report.

Blocked Conditions:

- Block when the report artifact, evidence registry, or report sections are unavailable.
- Block when the report or evidence cannot be checked for citation and section coverage.
