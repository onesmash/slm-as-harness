/verification-before-completion finalize the AI-assisted development delivery summary using {{design_summary}}, {{design_path}}, {{plan_summary}}, {{plan_path}}, {{implementation_summary}}, {{release_qa_verdict}}, {{review_status}}, {{reviewed_snapshot}}, {{completion_verification_passed}}, {{completion_verification_summary}}, {{completion_verification_evidence}}, {{completion_remaining_risks}}, {{subagent_review_approved}}, {{authorization_summary}}, and {{terminal_reason}} as branch-aware completion inputs. Empty fields for stages not reached are intentional and mean that evidence was not produced.

Stage Context:

- Design summary: {{design_summary}}
- Design path: {{design_path}}
- Plan summary: {{plan_summary}}
- Plan path: {{plan_path}}
- Implementation summary: {{implementation_summary}}
- Release QA verdict: {{release_qa_verdict}}
- Release QA executed checks: {{release_qa_executed_checks}}
- Release QA blocked checks: {{release_qa_blocked_checks}}
- Release QA risk next steps: {{release_qa_risk_next_steps}}
- Release QA artifacts: {{release_qa_artifacts}}
- Review status: {{review_status}}
- Reviewed snapshot: {{reviewed_snapshot}}
- Review findings: {{review_findings}}
- Completion verification passed: {{completion_verification_passed}}
- Completion verification summary: {{completion_verification_summary}}
- Completion verification evidence: {{completion_verification_evidence}}
- Completion remaining risks: {{completion_remaining_risks}}
- Subagent review authorization: {{subagent_review_approved}}
- Authorization summary: {{authorization_summary}}
- Terminal reason: {{terminal_reason}}
- Branch input rule: a blank field means its stage was not reached or the evidence is not applicable; report it as not executed rather than inferring success.

Stage Boundaries:

- If subagent review authorization was declined, report that the workflow closed before implementation planning; do not claim delivery completion or invent implementation evidence.
- If terminal reason is max_steps_exceeded, label the result as a degraded terminal summary and do not claim that delivery completion was proven.
- If a stage was not reached because authorization was declined or the budget was exhausted, summarize only the evidence available on that branch and omit normal-delivery claims.
- For the normal delivery branch, do not claim completion unless completion verification passed, release QA ended in ship, and pre-merge review ended in approved.
- Do not invent new implementation, QA, review, or verification facts that are not already grounded in the recorded workflow state.
- Keep the final summary concise and evidence-based so the user can reuse it as a handoff artifact.

Blocked Conditions:

- Block if the final completion evidence is missing or inconsistent for a normal delivery claim.
- Block if the workflow cannot produce a grounded final handoff summary from the recorded state.
