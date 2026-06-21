from workflows.common.contracts import (SkillRoute, SkillUseWhen, StepContract, StepVerifier, WorkflowInputContract)


WORKFLOW_ID = 'ios_ai_assisted_development_flow'

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={'goal': 'string', 'preferred_change_name': 'string?', 'mr_url': 'string?', 'kb_scope': 'string?'},
    context_schema={'repo_root': 'string',
 'source_doc_url': 'string?',
 'source_skill_url': 'string?',
 'openspec_source_url': 'string?'},
    constraints_schema={'max_steps': 'integer?', 'require_user_approval': 'boolean?'},
)

RUN_BRAINSTORMING_ROUTE_1 = SkillRoute(
    skill='brainstorming',
    use_when=SkillUseWhen(
        operations=['requirements clarification', 'design approval gate', 'design artifact preparation'],
        file_patterns=['docs/superpowers/specs/*.md'],
    ),
    usage_notes=['Primary owner for the pre-implementation approval gate.'],
)

RUN_BRAINSTORMING_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup', 'llms.txt discovery'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer only; do not write KB pages during brainstorming.'],
)

RUN_BRAINSTORMING_ROUTE_3 = SkillRoute(
    skill='software-design-philosophy',
    use_when=SkillUseWhen(
        operations=['development perspective spec review',
 'design decision review',
 'impact scope review',
 'implementation readiness review'],
        file_patterns=['docs/superpowers/specs/*.md'],
    ),
    usage_notes=['Supporting review lens for the required development-perspective spec review loop.'],
)

RUN_BRAINSTORMING = StepContract(
    done_when=['Clarification questions and answer summary are recorded.',
 'The user-approved design direction is recorded.',
 'The approved brainstorming design document exists under docs/superpowers/specs/ and its path is '
 'included.',
 'UI-impacting requests include implementation-ready visual detail and visual QA comparison inputs '
 'in the approved design document.',
 'The spec review loop has completed with independent development, design, and testing perspective '
 'reviews.'],
    output_schema={'clarification_questions': 'string[]',
 'clarification_answers_summary': 'string',
 'design_presented': 'boolean',
 'user_approved_design': 'boolean',
 'design_approved': 'boolean',
 'approved_design_summary': 'string',
 'approved_design_path': 'string',
 'ui_surface_affected': 'boolean',
 'visual_spec_detail_summary': 'string?',
 'design_comparison_source': 'string?',
 'runtime_visual_comparison_scope': 'string?',
 'spec_review_loop_completed': 'boolean',
 'spec_review_perspectives': 'string[]',
 'spec_review_findings_summary': 'string',
 'spec_review_subagent_summaries': 'string[]',
 'open_questions': 'string[]',
 'ready_for_openspec': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[RUN_BRAINSTORMING_ROUTE_1, RUN_BRAINSTORMING_ROUTE_2, RUN_BRAINSTORMING_ROUTE_3],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_run_brainstorming",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

PROPOSE_OPENSPEC_CHANGE_ROUTE_1 = SkillRoute(
    skill='openspec-propose',
    use_when=SkillUseWhen(
        operations=['change creation', 'proposal artifact generation', 'design/spec/tasks artifact generation'],
        file_patterns=['openspec/changes/**/proposal.md',
 'openspec/changes/**/design.md',
 'openspec/changes/**/tasks.md',
 'openspec/changes/**/specs/**/*.md'],
    ),
    usage_notes=['Primary owner for creating the durable OpenSpec change contract.'],
)

PROPOSE_OPENSPEC_CHANGE_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer for existing terminology and workflow docs.'],
)

PROPOSE_OPENSPEC_CHANGE = StepContract(
    done_when=['The OpenSpec change directory exists.',
 'Proposal, design/spec, and tasks artifacts are identified.',
 'The change is apply-ready or the missing formalization inputs are reported.'],
    output_schema={'change_name': 'string',
 'change_path': 'string',
 'proposal_path': 'string',
 'openspec_design_path': 'string?',
 'tasks_path': 'string',
 'spec_paths': 'string[]',
 'created_artifacts': 'string[]',
 'apply_ready': 'boolean'},
    failure_schema={'blocked_reason': 'string?',
 'error_message': 'string?',
 'missing_inputs': 'string[]?',
 'missing_artifacts': 'string[]?'},
    skill_routing=[PROPOSE_OPENSPEC_CHANGE_ROUTE_1, PROPOSE_OPENSPEC_CHANGE_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_propose_openspec_change",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REFINE_CHANGE_WITH_OPENSPEC_ROUTE_1 = SkillRoute(
    skill='openspec-explore',
    use_when=SkillUseWhen(
        operations=['artifact refinement', 'design ambiguity resolution', 'scope adjustment discussion'],
        file_patterns=['openspec/changes/**/*.md'],
    ),
    usage_notes=['Primary owner for thinking and refining after proposal, before apply.'],
)

REFINE_CHANGE_WITH_OPENSPEC_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer during OpenSpec refinement.'],
)

REFINE_CHANGE_WITH_OPENSPEC = StepContract(
    done_when=['At least one exploratory conversation turn has occurred with the user.',
 'Risks, ambiguities, and open questions have been surfaced and discussed.',
 'Unresolved questions are documented (even if empty, with user confirmation).',
 'The change is confirmed ready for apply after conversation.'],
    output_schema={'refinement_summary': 'string',
 'changed_artifacts': 'string[]',
 'unresolved_questions': 'string[]',
 'ready_for_apply': 'boolean'},
    failure_schema={'blocked_reason': 'string?',
 'error_message': 'string?',
 'missing_inputs': 'string[]?',
 'missing_artifacts': 'string[]?'},
    skill_routing=[REFINE_CHANGE_WITH_OPENSPEC_ROUTE_1, REFINE_CHANGE_WITH_OPENSPEC_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_refine_change_with_openspec",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

APPROVE_REFINE = StepContract(
    done_when=['The user has reviewed the refinement summary.',
 'The user has explicitly approved or rejected proceeding to implementation.'],
    output_schema={'user_approved': 'boolean', 'user_feedback': 'string?', 'additional_refinement_needed': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_approve_refine",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

EXECUTE_IMPLEMENTATION_ROUTE_1 = SkillRoute(
    skill='openspec-apply-change',
    use_when=SkillUseWhen(
        operations=['task implementation', 'task checkbox updates', 'verification evidence capture'],
        file_patterns=['openspec/changes/**/*.md', 'Zoom/**/*', 'Modules/**/*', 'MobileRTC/**/*'],
    ),
    usage_notes=['Primary owner for executing the OpenSpec tasks.'],
)

EXECUTE_IMPLEMENTATION_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer for existing terminology and workflow docs.'],
)

EXECUTE_IMPLEMENTATION_ROUTE_3 = SkillRoute(
    skill='xcodebuildmcp-cli',
    use_when=SkillUseWhen(
        operations=['iOS build verification',
 'iOS test verification',
 'iOS run or debug verification',
 'XcodeBuildMCP command discovery',
 'DerivedData path controlled verification'],
        file_patterns=['*.xcodeproj', '*.xcworkspace', 'Zoom/**/*', 'Modules/**/*', 'MobileRTC/**/*'],
    ),
    usage_notes=['Auxiliary owner for iOS build, test, run, debug, log, and UI automation verification.',
 'Discover DerivedData first with defaults read com.apple.dt.Xcode IDECustomDerivedDataLocation.',
 'Pass the returned path verbatim as --derived-data-path; do not append repo names, custom '
 'subdirectories, or MCP-private suffixes.',
 'Only use an MCP-private DerivedData path when the output records it explicitly as an environment '
 'fallback.'],
)

EXECUTE_IMPLEMENTATION_ROUTE_4 = SkillRoute(
    skill='manipulate-xcodeproj',
    use_when=SkillUseWhen(
        operations=['Xcode project file manipulation',
 'pbxproj group or file entry updates',
 'target membership updates',
 'build setting updates',
 'asset catalog updates'],
        file_patterns=['*.xcodeproj', '*.pbxproj', '*.xcassets', 'Zoom/**/*', 'Modules/**/*', 'MobileRTC/**/*'],
    ),
    usage_notes=['Auxiliary owner for editing .xcodeproj, .pbxproj, or .xcassets surfaces during implementation.',
 'Use XcodeProjectCLI via xcp only for project and asset catalog edits.',
 'Identify the .xcodeproj or .xcassets path first; for target-specific edits, run xcp list-targets '
 'before changing membership.',
 'Use --project-only when the project file should be updated without touching the filesystem, and '
 'verify with xcp list-targets or xcp list-assets when needed.'],
)

EXECUTE_IMPLEMENTATION = StepContract(
    done_when=['All selected OpenSpec implementation tasks are complete or the remaining blocked tasks are '
 'reported.',
 'Changed files are summarized.',
 'Verification commands and outcomes are reported.'],
    output_schema={'tasks_completed': 'boolean',
 'implementation_summary': 'string',
 'changed_files': 'string[]',
 'completed_tasks': 'string[]',
 'remaining_tasks': 'string[]',
 'verification_commands': 'string[]',
 'verification_passed': 'boolean',
 'open_issues': 'string[]'},
    failure_schema={'blocked_reason': 'string?',
 'error_message': 'string?',
 'missing_inputs': 'string[]?',
 'missing_artifacts': 'string[]?',
 'failed_commands': 'string[]?'},
    skill_routing=[EXECUTE_IMPLEMENTATION_ROUTE_1, EXECUTE_IMPLEMENTATION_ROUTE_2, EXECUTE_IMPLEMENTATION_ROUTE_3, EXECUTE_IMPLEMENTATION_ROUTE_4],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_execute_implementation",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_AGENTIC_RELEASE_QA_ROUTE_1 = SkillRoute(
    skill='agentic-release-qa',
    use_when=SkillUseWhen(
        operations=['change-aware release QA',
 'regression risk sweep',
 'executed versus blocked QA evidence',
 'release verdict synthesis'],
        file_patterns=['**/*'],
    ),
    usage_notes=['Primary owner for the post-implementation release QA gate before final merged-state review.'],
)

RUN_AGENTIC_RELEASE_QA_ROUTE_2 = SkillRoute(
    skill='pixel-diff',
    use_when=SkillUseWhen(
        operations=['runtime screenshot comparison',
 'design source visual comparison',
 'pixel-diff artifact generation',
 'visual regression risk reporting'],
        file_patterns=['*.png', '*.jpg', '*.jpeg', '*.webp', '**/screenshots/**', '**/snapshots/**'],
    ),
    usage_notes=['Auxiliary owner for UI-impacting release QA when a design comparison source and runtime '
 'screenshot scope are available.',
 'Compare the approved design, reference screenshot, or baseline image against the runtime app '
 'screenshot.',
 'Report executed visual checks, blocked visual checks, diff artifacts, and visual regression '
 'risks through the release QA output.'],
)

RUN_AGENTIC_RELEASE_QA = StepContract(
    done_when=['The QA pass identifies the code range or artifact under test.',
 'Change-derived release risks are summarized.',
 'Executed checks and blocked checks are reported separately.',
 'The release QA verdict is ship, ship_with_risks, do_not_ship, or blocked.',
 'Risk-based next steps are listed.'],
    output_schema={'release_qa_verdict': 'string',
 'release_qa_summary': 'string',
 'release_qa_executed_checks': 'string[]',
 'release_qa_blocked_checks': 'string[]',
 'release_qa_risk_next_steps': 'string[]',
 'release_qa_artifacts': 'string[]'},
    failure_schema={'blocked_reason': 'string?',
 'error_message': 'string?',
 'missing_inputs': 'string[]?',
 'failed_commands': 'string[]?'},
    skill_routing=[RUN_AGENTIC_RELEASE_QA_ROUTE_1, RUN_AGENTIC_RELEASE_QA_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_run_agentic_release_qa",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REQUEST_FINAL_CODE_REVIEW_ROUTE_1 = SkillRoute(
    skill='ios-gitlab-merged-mr-review',
    use_when=SkillUseWhen(
        operations=['MR metadata intake', 'merged-final file review', 'review finding synthesis'],
        file_patterns=['**/*.m', '**/*.mm', '**/*.h', '**/*.swift', '**/*.plist'],
    ),
    usage_notes=['Primary owner for the final code quality gate.'],
)

REQUEST_FINAL_CODE_REVIEW_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer for existing terminology and workflow docs.'],
)

REQUEST_FINAL_CODE_REVIEW = StepContract(
    done_when=['Review snapshot is identified.',
 'Findings are grouped by severity or explicitly reported as none.',
 'The review status is approved, changes_requested, or blocked.'],
    output_schema={'review_status': 'string',
 'reviewed_snapshot': 'string',
 'findings': 'string[]',
 'review_summary': 'string',
 'changes_requested': 'boolean',
 'missing_review_inputs': 'string[]'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[REQUEST_FINAL_CODE_REVIEW_ROUTE_1, REQUEST_FINAL_CODE_REVIEW_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_request_final_code_review",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

WRITE_CODE_KB_FEEDBACK_ROUTE_1 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['Stage 3 page refresh', 'Stage 4 QA feedback', 'backlog and llms.txt alignment'],
        file_patterns=['knowledge-base/**/*.md', 'knowledge-base/llms.txt', 'knowledge-base/_meta/*.md'],
    ),
    usage_notes=['Primary owner for durable knowledge feedback after implementation and review.'],
)

WRITE_CODE_KB_FEEDBACK = StepContract(
    done_when=['Knowledge-base updates are listed, or a skipped reason is provided.',
 'Backlog or QA feedback changes are summarized when applicable.',
 'Formatting or hygiene checks are reported when page updates were written.'],
    output_schema={'kb_updated': 'boolean',
 'updated_pages': 'string[]',
 'backlog_updates': 'string[]',
 'qa_feedback_path': 'string?',
 'kb_checks': 'string[]',
 'skipped_reason': 'string?'},
    failure_schema={'blocked_reason': 'string?',
 'error_message': 'string?',
 'missing_inputs': 'string[]?',
 'failed_commands': 'string[]?'},
    skill_routing=[WRITE_CODE_KB_FEEDBACK_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_write_code_kb_feedback",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REQUEST_UNBLOCKING_INPUT = StepContract(
    done_when=['Identify the blocking reason',
 'Ask the user for the input, approval, or resource required to continue'],
    output_schema={'blocking_reason': 'string', 'user_action_needed': 'string', 'suggested_next_input': 'string?'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
)

REPAIR_AND_RESUME = StepContract(
    done_when=['Explain why the original step needs repair',
 'Return retry_reason, retry_notes, and repair_actions'],
    output_schema={'retry_reason': 'string', 'retry_notes': 'string', 'repair_actions': 'string[]'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
)

STEP_CONTRACTS = {
    "run_brainstorming": RUN_BRAINSTORMING,
    "propose_openspec_change": PROPOSE_OPENSPEC_CHANGE,
    "refine_change_with_openspec": REFINE_CHANGE_WITH_OPENSPEC,
    "approve_refine": APPROVE_REFINE,
    "execute_implementation": EXECUTE_IMPLEMENTATION,
    "run_agentic_release_qa": RUN_AGENTIC_RELEASE_QA,
    "request_final_code_review": REQUEST_FINAL_CODE_REVIEW,
    "write_code_kb_feedback": WRITE_CODE_KB_FEEDBACK,
    "request_unblocking_input": REQUEST_UNBLOCKING_INPUT,
    "repair_and_resume": REPAIR_AND_RESUME,
}


def get_step_contract(step_id: str) -> StepContract:
    try:
        return STEP_CONTRACTS[step_id]
    except KeyError as exc:  # pragma: no cover - generated guard
        raise LookupError(f"unknown step contract: {step_id}") from exc


def list_step_contract_ids() -> list[str]:
    return list(STEP_CONTRACTS.keys())
