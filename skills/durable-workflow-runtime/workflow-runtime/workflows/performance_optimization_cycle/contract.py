from workflows.common.contracts import (SkillRoute, SkillUseWhen, StepContract, StepVerifier, WorkflowInputContract)


WORKFLOW_ID = 'performance_optimization_cycle'

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={'goal': 'string', 'baseline_cycles': 'integer?'},
    context_schema={'repo_root': 'string'},
    constraints_schema={},
)

DIAGNOSE_PERFORMANCE_ROUTE_1 = SkillRoute(
    skill='performance-nex',
    use_when=SkillUseWhen(
        operations=['performance baseline measurement', 'bottleneck diagnosis', 'capacity and latency analysis'],
        file_patterns=['.tmp/performance-nex/**'],
    ),
    usage_notes=['Primary owner for measured performance diagnosis before optimization ideation.'],
)

DIAGNOSE_PERFORMANCE = StepContract(
    done_when=['Baseline metrics and their measurement context are recorded.',
 'A dominant bottleneck and a diagnostic report path are recorded.',
 'The diagnosis is ready to constrain hypothesis generation.'],
    output_schema={'baseline_metrics': 'string',
 'bottleneck_summary': 'string',
 'performance_report_path': 'string',
 'ready_for_brainstorm': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[DIAGNOSE_PERFORMANCE_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.performance_optimization_cycle.verifiers:verify_diagnose_performance",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

BRAINSTORM_OPTIMIZATION_ROUTE_1 = SkillRoute(
    skill='brainstorming-nex',
    use_when=SkillUseWhen(
        operations=['optimization hypothesis generation', 'hypothesis scoring and shortlisting'],
        file_patterns=['.tmp/brainstorming-nex/**'],
    ),
    usage_notes=['Primary owner for optimization ideation and candidate shortlisting before research.'],
)

BRAINSTORM_OPTIMIZATION = StepContract(
    done_when=['At least one testable hypothesis is recorded.',
 'Success criteria and a scored ideation artifact path are recorded.',
 'The work is ready for evidence gathering.'],
    output_schema={'optimization_hypotheses': 'string[]',
 'success_criteria': 'string',
 'brainstorm_artifact_path': 'string',
 'ready_for_research': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[BRAINSTORM_OPTIMIZATION_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.performance_optimization_cycle.verifiers:verify_brainstorm_optimization",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RESEARCH_OPTIMIZATION_ROUTE_1 = SkillRoute(
    skill='research-nex',
    use_when=SkillUseWhen(
        operations=['evidence synthesis', 'technical opportunity analysis'],
        file_patterns=['.tmp/research-nex/**'],
    ),
    usage_notes=['Primary owner for research evidence; it must not publish the knowledge base.'],
)

RESEARCH_OPTIMIZATION = StepContract(
    done_when=['A research brief path, evidence summary, implementation-ready change summary, and verification '
 'plan are recorded.',
 'Implementation risks and open questions are explicit.'],
    output_schema={'research_brief_path': 'string',
 'evidence_summary': 'string',
 'open_risks': 'string[]',
 'planned_change_summary': 'string',
 'verification_plan': 'string[]',
 'ready_for_implementation': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[RESEARCH_OPTIMIZATION_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.performance_optimization_cycle.verifiers:verify_research_optimization",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

IMPLEMENT_OPTIMIZATION_ROUTE_1 = SkillRoute(
    skill='subagent-driven-development',
    use_when=SkillUseWhen(
        operations=['task-scoped implementation', 'task review', 'submission-test verification'],
        file_patterns=['perf_takehome.py', 'problem.py'],
    ),
    usage_notes=['Primary owner for direct implementation of the researched change with per-task review.'],
)

IMPLEMENT_OPTIMIZATION = StepContract(
    done_when=['The smallest testable change and verification commands are recorded.',
 'The implemented change and changed paths are recorded.',
 'python tests/submission_tests.py has passed.'],
    output_schema={'implementation_summary': 'string',
 'planned_change_summary': 'string',
 'verification_plan': 'string[]',
 'changed_paths': 'string[]',
 'submission_test_command': 'string',
 'submission_test_output': 'string',
 'submission_test_exit_code': 'integer',
 'submission_tests_passed': 'boolean',
 'ready_for_review': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[IMPLEMENT_OPTIMIZATION_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.performance_optimization_cycle.verifiers:verify_implement_optimization",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REVIEW_OPTIMIZATION_ROUTE_1 = SkillRoute(
    skill='requesting-code-review',
    use_when=SkillUseWhen(
        operations=['implementation review', 'constraint compliance review'],
        file_patterns=['perf_takehome.py', 'problem.py'],
    ),
    usage_notes=['Primary owner for review before knowledge-base maintenance.'],
)

REVIEW_OPTIMIZATION = StepContract(
    done_when=['Review findings and a readiness decision are recorded.'],
    output_schema={'review_summary': 'string', 'review_findings': 'string[]', 'ready_for_knowledge_base': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[REVIEW_OPTIMIZATION_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.performance_optimization_cycle.verifiers:verify_review_optimization",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

UPDATE_OPTIMIZATION_KNOWLEDGE_BASE_ROUTE_1 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['knowledge-base maintenance', 'optimization evidence documentation'],
        file_patterns=['knowledge-base/llms.txt', 'knowledge-base/_meta/*.md', 'knowledge-base/**/*.md'],
    ),
    usage_notes=['Primary owner for the durable knowledge-base update.'],
)

UPDATE_OPTIMIZATION_KNOWLEDGE_BASE = StepContract(
    done_when=['The updated knowledge-base artifacts and update summary are recorded.',
 'The workflow explicitly decides whether to start another optimization iteration.'],
    output_schema={'knowledge_base_update_summary': 'string',
 'knowledge_base_artifacts': 'string[]',
 'continue_optimization': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[UPDATE_OPTIMIZATION_KNOWLEDGE_BASE_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.performance_optimization_cycle.verifiers:verify_update_optimization_knowledge_base",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

CAPTURE_BLOCKED_CYCLE_KNOWLEDGE_ROUTE_1 = SkillRoute(
    skill='code-kb-workflow',
    use_when=SkillUseWhen(
        operations=['blocked-work documentation', 'optimization learning capture'],
        file_patterns=['knowledge-base/**/*.md', 'knowledge-base/llms.txt'],
    ),
    usage_notes=['Primary owner for recording blockers as reusable optimization knowledge before a new cycle.'],
)

CAPTURE_BLOCKED_CYCLE_KNOWLEDGE = StepContract(
    done_when=['A concise record of the blocked stage, blocker, evidence, and next-cycle lead is written to the '
 'knowledge base.',
 'The workflow is ready to begin a fresh performance diagnosis without waiting for user input.'],
    output_schema={'knowledge_base_update_summary': 'string',
 'knowledge_base_artifacts': 'string[]',
 'next_cycle_lead': 'string'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[CAPTURE_BLOCKED_CYCLE_KNOWLEDGE_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.performance_optimization_cycle.verifiers:verify_capture_blocked_cycle_knowledge",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REPAIR_AND_RESUME_ROUTE_1 = SkillRoute(
    skill='systematic-debugging',
    use_when=SkillUseWhen(
        operations=['root-cause investigation', 'verification-failure analysis'],
        file_patterns=['**/*'],
    ),
    usage_notes=['Primary owner for diagnosing verification failures before any implementation repair is '
 'attempted.'],
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
    skill_routing=[REPAIR_AND_RESUME_ROUTE_1],
)

STEP_CONTRACTS = {
    "diagnose_performance": DIAGNOSE_PERFORMANCE,
    "brainstorm_optimization": BRAINSTORM_OPTIMIZATION,
    "research_optimization": RESEARCH_OPTIMIZATION,
    "implement_optimization": IMPLEMENT_OPTIMIZATION,
    "review_optimization": REVIEW_OPTIMIZATION,
    "update_optimization_knowledge_base": UPDATE_OPTIMIZATION_KNOWLEDGE_BASE,
    "capture_blocked_cycle_knowledge": CAPTURE_BLOCKED_CYCLE_KNOWLEDGE,
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
