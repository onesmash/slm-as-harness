/report-nex {{workflow_goal}} using {{report_path}}, {{report_summary}}, {{report_sections}}, {{evidence_registry}}, {{coverage_map}}, {{coverage_assessment}}, {{next_round_validation_plan}}, {{report_scope_status}}, and {{output_dir}}; run this as a report-quality audit of an existing artifact in the invoked skill's M4 peer-review mode (`peer_review`), and independently verify section coverage, citation referential integrity, the final literal Evidence index for compact [n] markers, unsupported claims, duplication, coherence, and faithful disclosure of the Moderator's complete-or-partial scope decision, then return a structured pass or repair verdict.

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

- Audit the report without rewriting it: return concrete findings for the repair stage. This is a workflow instruction, not an independently enforced gate — no byte-level report immutability is verified here, and you have no pre-image to compare against, so never edit the file yourself and record under quality_findings anything you observe changing while you audit.
- Run this stage autonomously without pausing for user input: do not stop for user confirmation or mode selection and never ask a 'please select' or 'which mode' question; choose the audit framing yourself and return the verdict.
- This stage audits an existing artifact and produces no new report deliverable: do not re-route to a citation-audit, documentation, or research skill, and treat the audit dimensions named in this stage as the acceptance contract.
- Operate in the invoked skill's M4 peer-review mode (`peer_review`) with {{report_path}} as the artifact under review, returning a recommendation consistent with the findings; do not adopt its M2 academic-paper, M3 literature-review, M12 biomedical, M13 AI/ML, or M14 qualitative modes and do not switch to M5 scholar-evaluation scoring. Treat this stage's own audit dimensions as the acceptance contract.
- Treat every `[n] locator — claim` row in {{evidence_registry}} as the claim-ledger entry for citation n (claim_id = n, claim_text = the text after the first ` — `, evidence_ids = the row's locator, support_state = supported unless the claim is explicitly contested, verification_state = verified). No external claim_evidence_map, source_matrix, or verification_ledger exists and no ledger-schema validator run is required, so do not fail, defer, or degrade the audit because of it.
- Treat unknown citation identifiers, including numbers absent from the merged evidence_registry, missing section coverage, and unsupported substantive claims as failures.
- Treat number-only [n] body citations as valid only when the final literal Evidence index contains exactly one matching registry locator row; only the locator portion of an index row may be backtick-wrapped.
- Treat raw HTML blocks, fenced code, indented code, and inline code as non-report content: citation markers and index headings inside them are ignored, they never satisfy a citation requirement, and an Evidence index hidden that way does not count as the report's index. Cite claims in prose instead of relying on hidden markers. Malformed regions are not ignored: an unclosed fence, comment, or HTML block, and an Evidence index row hidden inside code, are all hard failures.
- A failed report verifier must still persist fail-closed audit fields (quality_verdict=repair, report_ready=false, findings including the verifier message) so repair_report can see them.
- A pass requires a report artifact, traceable citations, and no unresolved critical quality findings.
- A partial report may pass only when it contains the exact `Report scope: partial` marker and faithfully lists every unresolved topic id, open gap, validation metric, and next-round plan item; reject any partial report that presents itself as complete.
- A complete report may pass only when coverage_sufficient is true, next_round_validation_plan is empty, and the report contains the exact `Report scope: complete` marker.
- Return concrete findings and a pass or repair verdict without rewriting the report.
- Audit substance in addition to mechanics: the report must contain at least four substantive sections plus an executive summary; every substantive section must contain prose argumentation with at least two cited claims (bullet-only sections are a defect); the body must synthesize expert positions rather than list registry rows; depth and language must match the requirements expressed in {{workflow_goal}}.
- Return quality_verdict=repair with concrete quality_findings whenever the substance audit fails, even if citation mechanics pass, so the repair loop drives a substance-improving re-synthesis.
- Treat the single final Evidence index as a reference list, not body prose: its `- [n] locator` rows are this stage's sanctioned exception to the invoked skill's no-bullet-body rule and its prose/bullet pre-check, and they must not be hidden in code or converted to a table.

Blocked Conditions:

- Block when the report artifact, evidence registry, or report sections are unavailable.
- Block when the report or evidence cannot be checked for citation and section coverage.
