/report-nex {{workflow_goal}} using {{report_path}}, {{repair_summary}}, {{repair_requirements}}, {{repair_evidence}}, {{quality_findings}}, {{citation_coverage_summary}}, {{quality_verdict}}, and {{evidence_registry}}; translate audit findings into concrete repair actions including any missing or mismatched Evidence index rows and a handoff for the next synthesize_report pass without rewriting the report body in this stage.

Stage Context:

- Report path: {{report_path}}
- Verifier or recovery context from persisted repair state: {{repair_summary}}
- Repair requirements from persisted repair state: {{repair_requirements}}
- Repair evidence from persisted repair state: {{repair_evidence}}
- Quality findings from the failed report audit: {{quality_findings}}
- Citation coverage summary from the failed report audit: {{citation_coverage_summary}}
- Quality verdict from the failed report audit: {{quality_verdict}}
- Evidence registry: {{evidence_registry}}
- Knowledge-map summary: {{knowledge_map_summary}}

Stage Boundaries:

- Keep repairs limited to the report artifact and its evidence grounding; do not invent new research outside the shared evidence registry.
- Do not rewrite the report artifact in this recovery stage; return the repair plan for the next synthesize_report pass.
- Run this stage autonomously without pausing for user input: do not stop for user confirmation or mode selection and never ask a 'please select' or 'which mode' question; choose the repair framing yourself and return the repair plan.
- Treat every `[n] locator — claim` row in {{evidence_registry}} as the claim-ledger entry for citation n (claim_id = n, claim_text = the text after the first ` — `, evidence_ids = the row's locator). No external claim_evidence_map, source_matrix, or verification_ledger exists, so do not name a missing ledger among the repair actions.
- Return concrete repair actions and a handoff for the next report pass.
- Name every repair action that the next synthesis pass must apply.
- Name any missing or mismatched Evidence index rows by citation id and issue category so the next synthesize_report pass can restore the exact locator-only `- [n] locator` mapping without repeating long locators in the report body.
- Prefer fail-closed quality_verdict/quality_findings and repair_summary over any prior LLM pass verdict when the report verifier failed.
- Operate in the invoked skill's M1 technical-report mode (`tech_report`) and keep every repair action inside that report shape; do not adopt its M2/M3/M12/M13/M14 modes.
- Treat the single final Evidence index as a reference list, not body prose: its `- [n] locator` rows are this stage's sanctioned exception to the invoked skill's no-bullet-body rule and its prose/bullet pre-check, and they must not be hidden in code or converted to a table.

Blocked Conditions:

- Block when a concrete repair action cannot be derived from the available audit or repair context.
- Block when the report or evidence registry is unavailable.
