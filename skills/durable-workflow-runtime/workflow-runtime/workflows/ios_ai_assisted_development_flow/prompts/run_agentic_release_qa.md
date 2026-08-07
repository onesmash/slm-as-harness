/agentic-release-qa run a change-aware release QA pass for {{preferred_change_name}} in {{repo_root}} using changed files {{changed_files}}, implementation evidence {{implementation_summary}}, and verification commands {{verification_commands}}.

Stage Context:

- Preferred change name: {{preferred_change_name}}
- Workflow goal: {{goal}}
- Repository root: {{repo_root}}
- Changed files: {{changed_files}}
- Implementation summary: {{implementation_summary}}
- Verification commands: {{verification_commands}}
- Open issues: {{open_issues}}
- UI surface affected: {{ui_surface_affected}}
- Visual specification detail summary: {{visual_spec_detail_summary}}
- Design comparison source: {{design_comparison_source}}
- Runtime visual comparison scope: {{runtime_visual_comparison_scope}}
- Optional visual inputs: when UI surface affected or either comparison input is empty, report that visual comparison was not applicable or blocked; do not infer a design source or screenshot scope.

Stage Boundaries:

- Start from the actual changed files and implementation evidence instead of producing a generic release checklist.
- Separate executed QA evidence from blocked or recommended checks.
- Do not claim runtime, device, integration, or performance checks passed unless they were actually executed.
- Do not stress production systems or require destructive QA data without explicit user approval.
- Normalize release_qa_verdict to one of: ship or do_not_ship when the QA pass completes.
- Do not return release_qa_verdict=ship while blocked checks or other unresolved QA issues still remain.
- If required QA inputs are missing, return observation.status=blocked instead of encoding blocked as a succeeded release_qa_verdict.
- If ui_surface_affected is true and both design_comparison_source and runtime_visual_comparison_scope are available, include an explicit visual comparison pass and report the executed or blocked visual diff evidence.
- If ui_surface_affected is false, or the visual inputs are empty, do not claim visual QA was executed and do not invent visual evidence.
- Return the concrete QA target scope or artifact under test so later stages know exactly what was validated.

Blocked Conditions:

- Block if required QA environment, device, credentials, build artifact, or baseline data is missing and the missing input cannot be safely inferred.
- Block if the QA pass cannot identify the code range or artifact under test.
