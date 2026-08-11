/agentic-release-qa run a change-aware release QA pass for {{preferred_change_name}} in {{repo_root}} using changed files {{changed_files}}, implementation evidence {{implementation_summary}}, verification commands {{verification_commands}}, and device-QA mode {{agent_device_mode}} for app {{agent_device_app_id}} and artifact {{agent_device_artifact_path}}.

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
- Agent-device mode: {{agent_device_mode}}
- Agent-device app id: {{agent_device_app_id}}
- Agent-device artifact path: {{agent_device_artifact_path}}
- Agent-device target device: {{agent_device_device}}
- Agent-device session: {{agent_device_session}}
- Agent-device replay suite: {{agent_device_replay_suite}}
- Agent-device evidence directory: {{agent_device_evidence_dir}}
- Expected agent-device version: {{agent_device_expected_version}}
- Agent-device last status: {{agent_device_status}}
- Agent-device last commands: {{agent_device_commands}}
- Agent-device last artifacts: {{agent_device_artifacts}}
- Agent-device last session: {{agent_device_session}}
- Agent-device last replay suite: {{agent_device_replay_suite}}
- Agent-device observed CLI version: {{agent_device_cli_version}}
- Agent-device observed device: {{agent_device_observed_device}}
- Agent-device observed app id: {{agent_device_observed_app_id}}
- Agent-device runner status: {{agent_device_runner_status}}
- Agent-device execution receipt: {{agent_device_execution_receipt}}
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
- Keep agentic-release-qa as the primary release verdict owner; use agent-device only as a supporting device and runtime-evidence route.
- When agent_device_mode is off or empty, report that device QA was not requested and do not imply device evidence was executed.
- When agent_device_mode is required, record only actually executed agent-device commands and artifacts; missing version, device, app, runner, signing, or artifact inputs must be blocked.
- When agent_device_mode is required, write a bounded JSON execution receipt under the evidence directory with the current workflow run id, observed CLI/device/app/runner results, executed commands, build artifact, and evidence artifacts; return its path as agent_device_execution_receipt.
- For required device QA, allow the agent-device open handshake first, then validate the version-matched CLI and target preflight and prepare the iOS runner before snapshot, replay, test, or other device operations.
- Keep device mutations serial within one session and use the latest accessibility snapshot/ref/selector for follow-up actions.
- Use the evidence lifecycle open -> snapshot -i -> act with settle -> wait/get/is -> screenshot/logs/perf/trace -> replay or test -> close, recording only commands that actually ran.
- Return the concrete QA target scope or artifact under test so later stages know exactly what was validated.

Blocked Conditions:

- Block if required QA environment, device, credentials, build artifact, or baseline data is missing and the missing input cannot be safely inferred.
- Block if the QA pass cannot identify the code range or artifact under test.
- Block when agent_device_mode is required but the version-matched CLI, target device, installed app, runner preparation, signing, or evidence destination is unavailable.
