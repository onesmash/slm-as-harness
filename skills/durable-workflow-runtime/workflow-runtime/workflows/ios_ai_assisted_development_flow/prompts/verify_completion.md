/verification-before-completion verify {{change_name}} before final delivery using verification commands {{verification_commands}}, release QA verdict {{release_qa_verdict}}, review status {{review_status}}, reviewed snapshot {{reviewed_snapshot}}, review findings {{review_findings}}, open issues {{open_issues}}, and changed files {{changed_files}}.

Stage Context:

- Change name: {{change_name}}
- Changed files: {{changed_files}}
- Implementation summary: {{implementation_summary}}
- Verification commands: {{verification_commands}}
- Release QA verdict: {{release_qa_verdict}}
- Release QA summary: {{release_qa_summary}}
- Release QA executed checks: {{release_qa_executed_checks}}
- Release QA blocked checks: {{release_qa_blocked_checks}}
- Release QA risk next steps: {{release_qa_risk_next_steps}}
- Review status: {{review_status}}
- Reviewed snapshot: {{reviewed_snapshot}}
- Review findings: {{review_findings}}
- Review summary: {{review_summary}}
- Open issues: {{open_issues}}

Stage Boundaries:

- Do not claim the workflow is complete without fresh verification evidence gathered in this stage.
- Use the recorded verification commands, release QA results, and review findings as inputs, but re-check or freshly validate the evidence before approving completion.
- If release_qa_verdict is ship_with_risks, either resolve each residual QA risk with fresh evidence in this stage or return a non-passing result.
- If final verification finds missing evidence, unresolved risks, or failing checks, return a non-passing result instead of softening the outcome.
- Do not commit, push, create a PR, or imply merge readiness beyond the evidence produced here.

Blocked Conditions:

- Block if there is no concrete verification command, artifact, or review snapshot that can prove the completion claim.
- Block if the environment cannot run or inspect the required final verification evidence.
