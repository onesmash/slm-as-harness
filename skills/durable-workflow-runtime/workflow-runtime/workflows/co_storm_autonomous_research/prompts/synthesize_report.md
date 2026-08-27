/content-research-writer {{workflow_goal}} using {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, {{coverage_assessment}}, {{coverage_decision_rationale}}, {{next_round_validation_plan}}, {{report_scope_status}}, {{output_dir}}, and {{conversation_transcript}}; synthesize the autonomous Co-STORM knowledge space into a structured, cited report that uses compact [n] markers in the body, finishes with one literal `## Evidence index` section containing one exact locator row for each used marker, and preserves the Moderator's complete-or-partial scope decision for every substantive section.

Stage Context:

- Knowledge-map summary: {{knowledge_map_summary}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Moderator semantic coverage assessment: {{coverage_assessment}}
- Moderator coverage rationale: {{coverage_decision_rationale}}
- Outstanding next-round validation plan: {{next_round_validation_plan}}
- Report scope status: {{report_scope_status}}
- Configured output directory: {{output_dir}}
- Conversation transcript: {{conversation_transcript}}
- Requested deliverable: {{deliverable_type}}
- Previous report repair summary: {{report_repair_summary}}
- Concrete report repair actions to apply: {{repair_actions}}

Stage Boundaries:

- Do not introduce unsupported facts, uncited substantive claims, or sections absent from the knowledge map without marking them as limitations.
- Keep stable numeric [n] markers that match evidence_registry. Use number-only markers in the report body; do not emit or repeat any evidence_registry locator, URL, or file path beside claims.
- Finish the report with exactly one literal `## Evidence index` section. Add exactly one row in the form `- [n] locator` for every citation id used in the report body, copying only the locator from an evidence_registry row of the form `[n] locator — claim`; only the locator text in a row may have one surrounding Markdown-backtick pair, never the heading. Include no unused ids or substantive report text after this section. The verifier accepts a numeric heading prefix and the equivalent Chinese heading for compatibility with existing reports.
- Use at least two substantive Markdown sections and make the report_sections output list match their rendered headings exactly. Do not use raw HTML blocks, fenced code, indented code, or inline code to carry report claims, citations, or the Evidence index.
- Do not fabricate locators, URLs, or citation identifiers.
- Return the report artifact and its path before handoff.
- Do not declare final quality approval in this stage; return the report for an independent quality check.
- Include an exact `Report scope: complete` or `Report scope: partial` line. When partial, preserve every unresolved topic_id, open gap, validation metric, and top-level next-round plan item verbatim in a limitations and next-validation section; do not imply complete coverage.

Blocked Conditions:

- Block when the knowledge map or evidence registry is empty or internally inconsistent.
- Block when the report artifact is unavailable.
- Block when the requested deliverable type cannot be expressed as a cited structured report.
