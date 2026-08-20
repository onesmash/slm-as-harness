/audit-xls {{updated_model_path}} using {{audit_findings}} and {{audit_summary}}; repair critical workbook issues and leave the model ready to re-run the model-scope audit.

Stage Context:

- Updated model: {{updated_model_path}}
- Audit summary: {{audit_summary}}
- Audit findings: {{audit_findings}}

Stage Boundaries:

- Repair only the coverage model; do not draft or publish the note.
- Do not claim the audit passed in this stage; return to audit_coverage_model for verification.

Blocked Conditions:

- Block if the workbook cannot be opened or the failing cells cannot be identified.
