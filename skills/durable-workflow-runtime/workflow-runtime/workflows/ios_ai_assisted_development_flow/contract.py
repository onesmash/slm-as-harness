from workflows.common.contracts import (SkillRoute, SkillUseWhen, StepContract, StepVerifier, WorkflowInputContract)


WORKFLOW_ID = 'ios_ai_assisted_development_flow'

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={'goal': 'string', 'preferred_change_name': 'string?'},
    context_schema={'repo_root': 'string',
 'source_doc_url': 'string?',
 'source_skill_url': 'string?',
 'openspec_source_url': 'string?'},
    constraints_schema={'max_steps': 'integer?', 'require_user_approval': 'boolean?'},
)

RUN_BRAINSTORMING_ROUTE_1 = SkillRoute(
    skill='brainstorming',
    use_when=SkillUseWhen(
        operations=['requirements clarification',
 'design approval gate',
 'design artifact preparation',
 'multi-perspective spec review orchestration'],
        file_patterns=['docs/superpowers/specs/*.md'],
    ),
    usage_notes=['Primary owner for the pre-implementation approval gate.',
 'Owns the required development, design, and testing spec review loop before the stage completes.'],
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
 'The change artifacts are formalized and the current apply-readiness is reported.',
 'Artifact completeness is explicit enough to know whether proposal, design/spec, and tasks are '
 'all present.'],
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
 'The conversation evidence is summarized instead of jumping straight to structured output.',
 'Unresolved questions are documented (even if empty, with user confirmation).',
 'The change is confirmed ready for apply after conversation.'],
    output_schema={'refinement_summary': 'string',
 'user_discussion_summary': 'string',
 'discussion_turn_count': 'integer',
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
 'The user has explicitly approved implementation or requested another refinement pass.'],
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
 'open_issues': 'string[]',
 'openspec_updates_required': 'boolean?',
 'openspec_update_summary': 'string?'},
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
    usage_notes=['Primary owner for the post-implementation release QA gate before pre-merge code review.'],
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

REQUEST_PRE_MERGE_CODE_REVIEW_ROUTE_1 = SkillRoute(
    skill='requesting-code-review',
    use_when=SkillUseWhen(
        operations=['local diff review preparation',
 'base/head SHA selection',
 'pre-merge file review',
 'review finding synthesis'],
        file_patterns=['**/*.m', '**/*.mm', '**/*.h', '**/*.swift', '**/*.plist', '.git/**'],
    ),
    usage_notes=['Primary owner for the pre-merge code quality gate before MR creation or merge.'],
)

REQUEST_PRE_MERGE_CODE_REVIEW_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer for existing terminology and workflow docs.'],
)

REQUEST_PRE_MERGE_CODE_REVIEW_ROUTE_3 = SkillRoute(
    skill='ios-best-practices',
    use_when=SkillUseWhen(
        operations=['iOS-specific review standard lookup',
 'Swift and Objective-C review heuristics',
 'memory, threading, concurrency, and UIKit or SwiftUI review guidance',
 'architecture and security review guidance'],
        file_patterns=['**/*.m', '**/*.mm', '**/*.h', '**/*.swift', '**/*.plist'],
    ),
    usage_notes=['Supporting iOS review lens for evaluating changed files against Zoom iOS client best practices '
 'and regression patterns.'],
)

REQUEST_PRE_MERGE_CODE_REVIEW = StepContract(
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
    skill_routing=[REQUEST_PRE_MERGE_CODE_REVIEW_ROUTE_1, REQUEST_PRE_MERGE_CODE_REVIEW_ROUTE_2, REQUEST_PRE_MERGE_CODE_REVIEW_ROUTE_3],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_request_pre_merge_code_review",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

VERIFY_COMPLETION_ROUTE_1 = SkillRoute(
    skill='verification-before-completion',
    use_when=SkillUseWhen(
        operations=['fresh completion verification', 'verification evidence review', 'final delivery claim gate'],
        file_patterns=['**/*.m', '**/*.mm', '**/*.h', '**/*.swift', '**/*.plist', '.git/**'],
    ),
    usage_notes=['Primary owner for the final evidence-before-claims gate after review and before the workflow can '
 'summarize completion.'],
)

VERIFY_COMPLETION_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer for durable terminology, prior workflow documentation, and related '
 'verification guidance.'],
)

VERIFY_COMPLETION = StepContract(
    done_when=['Fresh completion verification evidence is recorded.',
 'Verification clearly reports whether completion can be claimed.',
 'Remaining risks or missing verification inputs are listed when verification does not pass.'],
    output_schema={'verification_passed': 'boolean',
 'verification_summary': 'string',
 'verification_evidence': 'string[]',
 'remaining_risks': 'string[]',
 'missing_verification_inputs': 'string[]',
 'release_qa_risks_resolved': 'boolean?',
 'release_qa_risk_resolution_summary': 'string?'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[VERIFY_COMPLETION_ROUTE_1, VERIFY_COMPLETION_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_verify_completion",
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
    "request_pre_merge_code_review": REQUEST_PRE_MERGE_CODE_REVIEW,
    "verify_completion": VERIFY_COMPLETION,
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
