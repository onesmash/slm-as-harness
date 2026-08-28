/content-research-writer {{workflow_goal}} using {{report_path}}, {{report_summary}}, {{report_sections}}, {{evidence_registry}}, {{coverage_map}}, {{coverage_assessment}}, {{next_round_validation_plan}}, {{report_scope_status}}, and {{output_dir}}; independently verify section coverage, citation referential integrity, the final literal Evidence index for compact [n] markers, unsupported claims, duplication, coherence, and faithful disclosure of the Moderator's complete-or-partial scope decision, then return a structured pass or repair verdict.

Stage Context:

- Report path: {{report_path}}
- Report summary: {{report_summary}}
- Report sections: {{report_sections}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Moderator semantic coverage assessment: {{coverage_assessment}}
- Outstanding next-round validation plan: {{next_round_validation_plan}}
- Report scope status: {{report_scope_status}}
- Configured output directory: {{output_dir}}
- Moderator coverage-sufficient flag: {{coverage_sufficient}}
- Knowledge-map summary: {{knowledge_map_summary}}

Stage Boundaries:

- Do not silently rewrite the report while performing verification; return concrete findings for the repair stage.
- Treat unknown citation identifiers, including numbers absent from the merged evidence_registry, missing section coverage, and unsupported substantive claims as failures.
- Treat number-only [n] body citations as valid only when the final literal Evidence index contains exactly one matching registry locator row; only the locator portion of an index row may be backtick-wrapped.
- Treat raw HTML blocks, fenced code, indented code, and inline code as non-report content and reject any citation or index hidden within them.
- A failed report verifier must still persist fail-closed audit fields (quality_verdict=repair, report_ready=false, findings including the verifier message) so repair_report can see them.
- A pass requires a report artifact, traceable citations, and no unresolved critical quality findings.
- A partial report may pass only when it contains the exact `Report scope: partial` marker and faithfully lists every unresolved topic id, open gap, validation metric, and next-round plan item; reject any partial report that presents itself as complete.
- A complete report may pass only when coverage_sufficient is true, next_round_validation_plan is empty, and the report contains the exact `Report scope: complete` marker.
- Return concrete findings and a pass or repair verdict without rewriting the report.
- Audit substance in addition to mechanics: the report must contain an executive summary; every substantive section must contain prose argumentation with at least two cited claims (bullet-only sections are a defect); the body must synthesize expert positions rather than list registry rows; depth and language must match the requirements expressed in {{workflow_goal}}.
- Return quality_verdict=repair with concrete quality_findings whenever the substance audit fails, even if citation mechanics pass, so the repair loop drives a substance-improving re-synthesis.

Blocked Conditions:

- Block when the report artifact, evidence registry, or report sections are unavailable.
- Block when the report or evidence cannot be checked for citation and section coverage.
