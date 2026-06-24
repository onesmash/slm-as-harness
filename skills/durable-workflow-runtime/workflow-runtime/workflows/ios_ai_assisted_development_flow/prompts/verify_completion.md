/verification-before-completion verify {{goal}} before final delivery using plan {{plan_path}}, verification commands {{verification_commands}}, release QA verdict {{release_qa_verdict}}, review status {{review_status}}, reviewed snapshot {{reviewed_snapshot}}, review findings {{review_findings}}, open issues {{open_issues}}, and changed files {{changed_files}}.

Stage Context:

- Plan path: {{plan_path}}
- Implementation summary: {{implementation_summary}}
- Verification commands: {{verification_commands}}
- Release QA verdict: {{release_qa_verdict}}
- Release QA summary: {{release_qa_summary}}
- Release QA target scope: {{release_qa_target_scope}}
- Release QA blocked checks: {{release_qa_blocked_checks}}
- Release QA risk next steps: {{release_qa_risk_next_steps}}
- Review status: {{review_status}}
- Review findings: {{review_findings}}
- Open issues: {{open_issues}}
- Latest release QA risk resolution summary: {{completion_release_qa_risk_resolution_summary}}

Stage Boundaries:

- Do not claim the workflow is complete without fresh verification evidence gathered in this stage.
- Use the recorded verification commands, release QA results, and review findings as inputs, but re-check or freshly validate the evidence before approving completion.
- If completion cannot be proven because required verification inputs or external evidence are missing, return observation.status=blocked instead of a succeeded payload with unresolved missing_verification_inputs.
- Do not treat the workflow as complete unless release QA finished with ship and pre-merge code review finished with approved.
- If final verification finds missing evidence, unresolved risks, or failing checks, return a non-passing result instead of softening the outcome.
- Do not commit, push, create a PR, or imply merge readiness beyond the evidence produced here.

Blocked Conditions:

- Block if there is no concrete verification command, artifact, or review snapshot that can prove the completion claim.
- Block if the environment cannot run or inspect the required final verification evidence.
