/subagent-driven-development execute {{plan_path}} in {{repo_root}}; follow /test-driven-development for behavior changes and /systematic-debugging before any fix when tests or verification fail.

Stage Context:

- Plan path: {{plan_path}}
- Plan summary: {{plan_summary}}
- Approved design path: {{approved_design_path}}
- Approved design summary: {{approved_design_summary}}
- Plan approval feedback: {{plan_user_feedback}}
- Plan revision reason: {{plan_revision_reason}}
- Latest completed tasks: {{implementation_completed_tasks}}
- Latest remaining tasks: {{implementation_remaining_tasks}}
- Latest implementation verification passed: {{implementation_verification_passed}}
- Latest plan update summary: {{plan_update_summary}}
- Latest debugging summary: {{debugging_summary}}
- Latest open issues: {{open_issues}}
- Latest release QA verdict: {{release_qa_verdict}}
- Latest release QA summary: {{release_qa_summary}}
- Latest release QA blocked checks: {{release_qa_blocked_checks}}
- Latest release QA risk next steps: {{release_qa_risk_next_steps}}
- Latest release QA artifacts: {{release_qa_artifacts}}
- Latest release QA target scope: {{release_qa_target_scope}}
- Latest review status: {{review_status}}
- Latest review findings: {{review_findings}}
- Latest completion verification summary: {{completion_verification_summary}}
- Latest completion verification evidence: {{completion_verification_evidence}}
- Latest completion remaining risks: {{completion_remaining_risks}}
- Latest completion missing verification inputs: {{completion_missing_verification_inputs}}
- Latest completion release QA risk resolution summary: {{completion_release_qa_risk_resolution_summary}}

Stage Boundaries:

- Keep edits scoped to the approved design and written implementation plan.
- Use subagent-driven-development as the primary execution path.
- Use test-driven-development for behavior changes before writing production code.
- If verification fails or behavior is unexpected, route through systematic-debugging before changing the fix direction.
- If implementation exposes a plan or design issue, return enough structured detail to route back into planning instead of improvising around the gap.
- Do not commit, push, or create an MR unless the user separately asks for it.
- Leave the change in a state that can be inspected by the later pre-merge code review using the local diff, branch state, and recorded verification evidence.
- When this stage is re-entered after release QA, code review, or completion verification, explicitly address the recorded failure context instead of re-running the plan blindly.

Blocked Conditions:

- Block if a plan task is ambiguous.
- Block if implementation reveals a design or plan issue that requires plan updates.
- Block if verification cannot run because a required environment dependency is unavailable.
