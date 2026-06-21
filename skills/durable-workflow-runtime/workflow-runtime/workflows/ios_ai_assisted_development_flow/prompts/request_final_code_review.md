/ios-gitlab-merged-mr-review review {{mr_url}} for {{change_name}} using changed files {{changed_files}}, implementation evidence {{implementation_summary}}, and release QA verdict {{release_qa_verdict}}.

Stage Context:

- Change name: {{change_name}}
- MR URL: {{mr_url}}
- Changed files: {{changed_files}}
- Implementation summary: {{implementation_summary}}
- Verification commands: {{verification_commands}}
- Release QA verdict: {{release_qa_verdict}}
- Release QA summary: {{release_qa_summary}}
- Release QA executed checks: {{release_qa_executed_checks}}
- Release QA blocked checks: {{release_qa_blocked_checks}}
- Release QA risk next steps: {{release_qa_risk_next_steps}}
- Open issues: {{open_issues}}

Stage Boundaries:

- Prioritize findings, regressions, risky behavior changes, and missing tests.
- Consider release QA risks and blocked checks when judging merge safety.
- If release_qa_verdict is ship_with_risks, explicitly assess each release_qa_blocked_checks item and carry unresolved QA risks into the merge-safety decision.
- Use merged-final state when an MR URL and merge snapshot are available.
- If no MR URL or review snapshot is available, block and request the missing review handle.

Blocked Conditions:

- Block if no MR URL, merge commit, or equivalent review snapshot is available.
- Block if GitLab access is unavailable.
