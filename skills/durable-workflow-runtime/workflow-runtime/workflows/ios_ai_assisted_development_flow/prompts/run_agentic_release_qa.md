/agentic-release-qa run a change-aware release QA pass for {{change_name}} in {{repo_root}} using changed files {{changed_files}}, implementation evidence {{implementation_summary}}, and verification commands {{verification_commands}}.

Stage Context:

- Change name: {{change_name}}
- Repository root: {{repo_root}}
- Changed files: {{changed_files}}
- Implementation summary: {{implementation_summary}}
- Verification commands: {{verification_commands}}
- Open issues: {{open_issues}}
- MR URL: {{mr_url}}

Stage Boundaries:

- Start from the actual changed files and implementation evidence instead of producing a generic release checklist.
- Separate executed QA evidence from blocked or recommended checks.
- Do not claim runtime, device, integration, or performance checks passed unless they were actually executed.
- Do not stress production systems or require destructive QA data without explicit user approval.
- Normalize release_qa_verdict to one of: ship, ship_with_risks, do_not_ship, blocked.

Blocked Conditions:

- Block if required QA environment, device, credentials, build artifact, or baseline data is missing and the missing input cannot be safely inferred.
- Block if the QA pass cannot identify the code range or artifact under test.
