/content-research-writer {{workflow_goal}} using {{report_path}}, {{repair_summary}}, {{repair_requirements}}, {{repair_evidence}}, {{quality_findings}}, {{citation_coverage_summary}}, {{quality_verdict}}, and {{evidence_registry}}; translate audit findings into concrete repair actions including any missing in-place source locators and a handoff for the next synthesize_report pass without rewriting the report body in this stage.

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
- Return concrete repair actions and a handoff for the next report pass.
- Name every repair action that the next synthesis pass must apply.
- Name any missing in-place source locators so the next synthesize_report pass can restore path/URL/file:line text beside [n] markers.
- Prefer fail-closed quality_verdict/quality_findings and repair_summary over any prior LLM pass verdict when the report verifier failed.

Blocked Conditions:

- Block when a concrete repair action cannot be derived from the available audit or repair context.
- Block when the report or evidence registry is unavailable.
