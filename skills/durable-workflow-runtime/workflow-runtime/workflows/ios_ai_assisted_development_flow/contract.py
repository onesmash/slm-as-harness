from workflows.common.contracts import (SkillRoute, SkillUseWhen, StepContract, StepVerifier, WorkflowInputContract)


WORKFLOW_ID = 'ios_ai_assisted_development_flow'

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={'goal': 'string', 'preferred_change_name': 'string?'},
    context_schema={'repo_root': 'string', 'source_doc_url': 'string?', 'source_skill_url': 'string?'},
    constraints_schema={'max_steps': 'integer?', 'require_user_approval': 'boolean?'},
)

RUN_BRAINSTORMING_ROUTE_1 = SkillRoute(
    skill='brainstorming-nex',
    use_when=SkillUseWhen(
        operations=['requirements clarification', 'design approval gate', 'design artifact preparation'],
        file_patterns=['docs/superpowers/specs/*.md'],
    ),
    usage_notes=['Primary owner for the pre-implementation design clarification and approval gate.',
 'Owns the approved design package that will later be handed into the review-authorization and '
 'subagent-review stages.'],
)

RUN_BRAINSTORMING_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup', 'llms.txt discovery'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer only; do not write KB pages during brainstorming.'],
)

RUN_BRAINSTORMING = StepContract(
    done_when=['Clarification questions and answer summary are recorded.',
 'The user-approved design direction is recorded.',
 'The approved brainstorming design document exists under docs/superpowers/specs/ and its path is '
 'included.',
 'UI-impacting requests include implementation-ready visual detail and visual QA comparison inputs '
 'in the approved design document.',
 'The approved design package is ready for an explicit subagent review authorization decision.'],
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
 'open_questions': 'string[]',
 'ready_for_subagent_review': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[RUN_BRAINSTORMING_ROUTE_1, RUN_BRAINSTORMING_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_run_brainstorming",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

APPROVE_SUBAGENT_REVIEW_ROUTE_1 = SkillRoute(
    skill='brainstorming-nex',
    use_when=SkillUseWhen(
        operations=['user approval gate', 'subagent review authorization request'],
        file_patterns=['docs/superpowers/specs/*.md'],
    ),
    usage_notes=['Primary owner for asking whether the required review subagents may be launched.'],
)

APPROVE_SUBAGENT_REVIEW = StepContract(
    done_when=['The user has explicitly approved or declined the required subagent design review pass.',
 'The authorization decision is summarized for the next stage or workflow closeout.'],
    output_schema={'subagent_review_approved': 'boolean',
 'authorization_summary': 'string',
 'ready_for_spec_review': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[APPROVE_SUBAGENT_REVIEW_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_approve_subagent_review",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_SPEC_REVIEW_ROUTE_1 = SkillRoute(
    skill='brainstorming-nex',
    use_when=SkillUseWhen(
        operations=['multi-perspective spec review orchestration',
 'subagent review artifact handoff',
 'implementation readiness confirmation'],
        file_patterns=['docs/superpowers/specs/*.md'],
    ),
    usage_notes=['Primary owner for orchestrating the independent review loop and collecting the concrete review '
 'artifacts.'],
)

RUN_SPEC_REVIEW_ROUTE_2 = SkillRoute(
    skill='software-design-philosophy',
    use_when=SkillUseWhen(
        operations=['development perspective spec review',
 'design decision review',
 'impact scope review',
 'implementation readiness review'],
        file_patterns=['docs/superpowers/specs/*.md'],
    ),
    usage_notes=['Supporting review lens for the development-oriented portion of the independent spec review loop.'],
)

RUN_SPEC_REVIEW = StepContract(
    done_when=['Concrete review artifacts from the development, design, and testing subagent reviews are handed '
 'in.',
 'The spec review loop has completed with independent development, design, and testing perspective '
 'reviews.',
 'Implementation-planning readiness or required design rework is recorded.'],
    output_schema={'spec_review_loop_completed': 'boolean',
 'spec_review_perspectives': 'string[]',
 'spec_review_findings_summary': 'string',
 'spec_review_subagent_summaries': 'string[]',
 'spec_review_artifact_paths': 'string[]',
 'open_questions': 'string[]',
 'ready_for_planning': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[RUN_SPEC_REVIEW_ROUTE_1, RUN_SPEC_REVIEW_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_run_spec_review",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

WRITE_IMPLEMENTATION_PLAN_ROUTE_1 = SkillRoute(
    skill='writing-plans',
    use_when=SkillUseWhen(
        operations=['implementation plan authoring', 'task decomposition', 'execution handoff selection'],
        file_patterns=['docs/superpowers/plans/*.md', 'docs/superpowers/specs/*.md'],
    ),
    usage_notes=['Primary owner for turning the approved design into a detailed implementation plan.',
 'Must record subagent-driven as the execution mode required by this workflow without asking the '
 'user to choose alternatives.'],
)

WRITE_IMPLEMENTATION_PLAN_ROUTE_2 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer for existing terminology and workflow docs.'],
)

WRITE_IMPLEMENTATION_PLAN = StepContract(
    done_when=['The implementation plan exists under docs/superpowers/plans/.',
 'The plan summary is recorded.',
 'The user has reviewed the written plan.',
 'The execution mode is recorded as subagent-driven and is ready for implementation.'],
    output_schema={'plan_summary': 'string',
 'plan_path': 'string',
 'plan_reviewed': 'boolean',
 'execution_mode': 'string',
 'open_questions': 'string[]',
 'ready_for_implementation': 'boolean',
 'plan_revision_reason': 'string?'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[WRITE_IMPLEMENTATION_PLAN_ROUTE_1, WRITE_IMPLEMENTATION_PLAN_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.ios_ai_assisted_development_flow.verifiers:verify_write_implementation_plan",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

EXECUTE_IMPLEMENTATION_ROUTE_1 = SkillRoute(
    skill='subagent-driven-development',
    use_when=SkillUseWhen(
        operations=['plan execution', 'task-by-task implementation', 'review-driven iteration'],
        file_patterns=['docs/superpowers/plans/*.md',
 '**/*.m',
 '**/*.mm',
 '**/*.h',
 '**/*.swift',
 '*.xcodeproj',
 '*.xcworkspace'],
    ),
    usage_notes=['Primary owner for executing the approved implementation plan.'],
)

EXECUTE_IMPLEMENTATION_ROUTE_2 = SkillRoute(
    skill='test-driven-development',
    use_when=SkillUseWhen(
        operations=['red-green-refactor loops', 'regression test creation'],
        file_patterns=['**/test*.py', '**/*test*.*', '**/*.swift', '**/*.m', '**/*.mm'],
    ),
    usage_notes=['Auxiliary owner for behavior-changing implementation work before production edits.'],
)

EXECUTE_IMPLEMENTATION_ROUTE_3 = SkillRoute(
    skill='systematic-debugging',
    use_when=SkillUseWhen(
        operations=['root cause investigation', 'verification failure diagnosis'],
        file_patterns=['**/*.m', '**/*.mm', '**/*.h', '**/*.swift', '**/*test*.*'],
    ),
    usage_notes=['Auxiliary owner whenever tests, builds, or runtime verification fail during implementation.'],
)

EXECUTE_IMPLEMENTATION_ROUTE_4 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base context lookup'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Supporting context layer for existing terminology and workflow docs.'],
)

EXECUTE_IMPLEMENTATION_ROUTE_5 = SkillRoute(
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

EXECUTE_IMPLEMENTATION_ROUTE_6 = SkillRoute(
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
    done_when=['All selected implementation tasks are complete or the remaining blocked tasks are reported.',
 'Changed files are summarized.',
 'Verification commands and outcomes are reported.',
 'Any debugging or plan-update requirement is summarized explicitly.'],
    output_schema={'tasks_completed': 'boolean',
 'implementation_summary': 'string',
 'changed_files': 'string[]',
 'completed_tasks': 'string[]',
 'remaining_tasks': 'string[]',
 'verification_commands': 'string[]',
 'verification_passed': 'boolean',
 'open_issues': 'string[]',
 'debugging_summary': 'string?',
 'plan_updates_required': 'boolean?',
 'plan_update_summary': 'string?'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[EXECUTE_IMPLEMENTATION_ROUTE_1, EXECUTE_IMPLEMENTATION_ROUTE_2, EXECUTE_IMPLEMENTATION_ROUTE_3, EXECUTE_IMPLEMENTATION_ROUTE_4, EXECUTE_IMPLEMENTATION_ROUTE_5, EXECUTE_IMPLEMENTATION_ROUTE_6],
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
 'The release QA verdict is ship or do_not_ship when the stage completes successfully.',
 'A ship verdict means there are no blocked checks left in the QA result.',
 'Risk-based next steps are listed.'],
    output_schema={'release_qa_verdict': 'string',
 'release_qa_summary': 'string',
 'release_qa_executed_checks': 'string[]',
 'release_qa_blocked_checks': 'string[]',
 'release_qa_risk_next_steps': 'string[]',
 'release_qa_artifacts': 'string[]',
 'release_qa_target_scope': 'string'},
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
 'An approved review means no actionable findings remain.',
 'The review status is approved or changes_requested when the stage completes successfully.'],
    output_schema={'review_status': 'string',
 'reviewed_snapshot': 'string',
 'findings': 'string[]',
 'review_summary': 'string',
 'changes_requested': 'boolean'},
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
 'Remaining risks are listed when verification completes without passing.'],
    output_schema={'verification_passed': 'boolean',
 'verification_summary': 'string',
 'verification_evidence': 'string[]',
 'remaining_risks': 'string[]',
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

REPAIR_AND_RESUME_ROUTE_1 = SkillRoute(
    skill='research-nex',
    use_when=SkillUseWhen(
        operations=['repair solution exploration', 'evidence-backed option synthesis', 'failure mode research'],
        file_patterns=['*.md', '*.swift', '*.m', '*.mm', '*.pbxproj', '*.log'],
    ),
    usage_notes=['Primary owner for researching plausible repair strategies and retry guidance from the persisted '
 'repair context.',
 'Keep the stage focused on solution exploration and evidence synthesis; do not use it as the '
 'implementation owner.'],
)

REPAIR_AND_RESUME_ROUTE_2 = SkillRoute(
    skill='search-nex',
    use_when=SkillUseWhen(
        operations=['targeted source discovery', 'first-pass verification for repair research'],
        file_patterns=['*.md', '*.swift', '*.m', '*.mm', '*.pbxproj', '*.log'],
    ),
    usage_notes=['Supporting route for finding fresh sources or references that research-nex should synthesize '
 'before the workflow retries the return stage.'],
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
    output_schema={'retry_reason': 'string',
 'retry_notes': 'string',
 'repair_actions': 'string[]',
 'needs_external_unblocking': 'boolean?'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[REPAIR_AND_RESUME_ROUTE_1, REPAIR_AND_RESUME_ROUTE_2],
)

STEP_CONTRACTS = {
    "run_brainstorming": RUN_BRAINSTORMING,
    "approve_subagent_review": APPROVE_SUBAGENT_REVIEW,
    "run_spec_review": RUN_SPEC_REVIEW,
    "write_implementation_plan": WRITE_IMPLEMENTATION_PLAN,
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
