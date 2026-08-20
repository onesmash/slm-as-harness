/audit-xls {{updated_model_path}} at model scope; record audit findings and echo skip_note from workflow state before any note draft.

Stage Context:

- Ticker: {{ticker}}
- Reporting period: {{reporting_period}}
- Updated model: {{updated_model_path}}
- Variance rows: {{variance_rows}}
- Estimate changes: {{estimate_change_summary}}
- Skip note: {{skip_note}}
- Model-builder handoff target: {{handoff_target}}
- Model-builder handoff reason: {{handoff_reason}}

Stage Boundaries:

- Use model scope, not selection or sheet-only scope.
- Do not change the workbook in this stage; repairs belong to repair_model_audit.
- Do not draft or publish the note in this stage.
- Echo skip_note from workflow state so routing can skip the note when requested.
- Critical findings must be resolved before model_audit_ready is true.

Blocked Conditions:

- Block if the updated workbook path is missing or unreadable.
