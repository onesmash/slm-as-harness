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
- context.output_dir is a repository-relative path (never absolute, never starting with '/'). report_path must be repository-relative and must resolve inside context.output_dir; write the report artifact under that directory and return its repo-relative path.
- report_sections must equal the report's rendered Markdown ## headings, normalized: strip a leading numeric prefix like '1. ', strip any trailing parenthesized note, and keep punctuation exactly (顿号 included). Compare ONLY the headings that appear in the report body BEFORE the final '## Evidence index' heading — never include 'Evidence index' itself in report_sections.
- The report must contain exactly one literal line, either `Report scope: complete` or `Report scope: partial` matching report_scope_status, somewhere before the Evidence index.
- Never repeat any evidence_registry locator text in the report body — not even inside a narrative sentence such as mentioning a filename that happens to equal a locator (e.g. 'Cargo.toml'); the body may only use compact [n] markers. The Evidence index is the only place locators appear.
- Produce a substantive report: 4 to 8 Markdown sections before the Evidence index (executive summary plus at least three deep sections), each section developing its claims in prose with at least two [n] citations; bullet-only sections and reports that merely restate registry rows are defective deliverables.
- Start with an executive summary as a level-2 Markdown `## Executive summary` heading (so it counts as a substantive section), under one page, stating the research question, the main conclusions with [n] citations, and the overall confidence level.
- Synthesize across the expert perspectives recorded in {{conversation_transcript}}: when experts disagree, present both positions with their evidence and note the disagreement; when they agree, state the convergence explicitly.
- Where {{evidence_registry}} and {{coverage_map}} support comparing approaches, options, or versions, use a comparison table with [n]-cited factual cells; keep table cells to prose, data, and [n] markers only — never place registry locators, URLs, or file paths in cells, and never use bare bracketed numbers in tables unless they are registry citation ids.
- Match language and depth to the requested deliverable: comply with language and length requirements expressed in {{deliverable_type}} or {{workflow_goal}} (for example 中文, 5000字); when none are given, write in the language of {{workflow_goal}} and aim for 1200-3000 words for standard overviews and 3000-8000 words for deep deliverables.
- Flag uncertainty inline where evidence is thin or contested (for example '证据较弱', '存在争议'), and keep every open gap in the limitations section when the report scope is partial.
- Begin the report with exactly one top-level `# ` H1 title heading (the research question or deliverable title), followed by the executive summary; all other sections use `##` headings.

Blocked Conditions:

- Block when the knowledge map or evidence registry is empty or internally inconsistent.
- Block when the report artifact is unavailable.
- Block when the requested deliverable type cannot be expressed as a cited structured report.
