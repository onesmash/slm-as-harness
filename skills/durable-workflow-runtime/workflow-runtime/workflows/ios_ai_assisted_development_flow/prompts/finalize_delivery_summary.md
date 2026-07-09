/verification-before-completion finalize the iOS Client AI-assisted development delivery summary using {{design_summary}}, {{design_path}}, {{plan_summary}}, {{plan_path}}, {{implementation_summary}}, {{release_qa_verdict}}, {{review_status}}, and {{completion_verification_passed}} as the minimum completion inputs.

Stage Context:

- Design summary: {{design_summary}}
- Design path: {{design_path}}
- Plan summary: {{plan_summary}}
- Plan path: {{plan_path}}
- Implementation summary: {{implementation_summary}}
- Release QA verdict: {{release_qa_verdict}}
- Review status: {{review_status}}
- Completion verification passed: {{completion_verification_passed}}

Stage Boundaries:

- Do not claim delivery completion unless the completion verification stage has passed.
- Do not invent new implementation or QA facts that are not already grounded in the recorded workflow state.
- Keep the final summary concise and evidence-based so the user can reuse it as a handoff artifact.

Blocked Conditions:

- Block if the final completion evidence is missing or inconsistent.
- Block if the workflow cannot produce a grounded final handoff summary from the recorded state.
