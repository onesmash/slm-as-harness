/requesting-code-review request a pre-merge code review for {{change_name}} using changed files {{changed_files}}, implementation evidence {{implementation_summary}}, verification commands {{verification_commands}}, and release QA verdict {{release_qa_verdict}}. Review the current local git diff or branch state before merge, derive the review snapshot from available git history, and return findings plus a merge-readiness decision.

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
- Supplemental review standard: apply ios-best-practices to the touched iOS files for memory management, threading, concurrency, UIKit or SwiftUI usage, architecture, security, and regression-sensitive patterns.
- Open issues: {{open_issues}}

Stage Boundaries:

- Prioritize findings, regressions, risky behavior changes, and missing tests.
- Consider release QA risks and blocked checks when judging merge safety.
- Use ios-best-practices as an explicit iOS review lens for Swift, Objective-C, UIKit, SwiftUI, memory, concurrency, security, and architecture concerns in the changed files.
- If release_qa_verdict is ship_with_risks, explicitly assess each release_qa_blocked_checks item and carry unresolved QA risks into the merge-safety decision.
- Prefer reviewing the current local git diff or branch state instead of requiring a published MR.
- If findings exist, group them by severity and make the severity obvious in the returned finding strings.
- If a suitable git review range or snapshot cannot be determined because external review inputs are missing, block and request the missing review input.

Blocked Conditions:

- Block if no usable git diff, base SHA, head SHA, branch snapshot, or equivalent review range can be determined because a required review input is missing.
- Fail instead of blocking when the repository state is corrupted, unreadable, or the review tooling errors after the review range is known.
