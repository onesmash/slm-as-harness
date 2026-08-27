from workflows.common.contracts import (SkillRoute, SkillUseWhen, StepContract, StepVerifier, WorkflowInputContract)


WORKFLOW_ID = 'co_storm_autonomous_research'

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={'goal': 'string',
 'deliverable_type': 'string?',
 'research_scope': 'string?',
 'source_policy': 'string?'},
    context_schema={'repo_root': 'string', 'source_materials_path': 'string?', 'output_dir': 'string?'},
    constraints_schema={'max_steps': 'integer?',
 'max_rounds': 'integer?',
 'min_evidence_items': 'integer?',
 'coverage_threshold': 'integer?',
 'max_reorganizations': 'integer?'},
)

WARM_START_SHARED_SPACE_ROUTE_1 = SkillRoute(
    skill='research-nex',
    use_when=SkillUseWhen(
        operations=['autonomous perspective generation',
 'grounded background research',
 'evidence registry construction'],
        file_patterns=[],
    ),
    usage_notes=['Primary owner for the Co-STORM warm-start research package.'],
)

WARM_START_SHARED_SPACE = StepContract(
    done_when=['At least two complementary expert perspectives are recorded.',
 'The warm-start transcript contains grounded research turns.',
 'The knowledge-map summary and coverage baseline are non-empty.',
 'The evidence registry contains stable citation identifiers and source locators.',
 'The shared space is ready for independent expert result collection.'],
    output_schema={'expert_roster': 'object[]',
 'conversation_transcript': 'string[]',
 'knowledge_map_summary': 'string',
 'evidence_registry': 'string[]',
 'coverage_map': 'string[]',
 'round_index': 'integer',
 'warm_start_ready': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[WARM_START_SHARED_SPACE_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.co_storm_autonomous_research.verifiers:verify_warm_start_shared_space",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

LAUNCH_EXPERT_SUBAGENTS_ROUTE_1 = SkillRoute(
    skill='research-nex',
    use_when=SkillUseWhen(
        operations=['independent expert perspective collection',
 'grounded result collection',
 'expert retrieval and evidence merge',
 'expert result artifact handoff'],
        file_patterns=[],
    ),
    usage_notes=['Primary owner for collecting one independent, grounded result for each expert; subagents may '
 'retrieve, but this stage owns global citation numbering.'],
)

LAUNCH_EXPERT_SUBAGENTS_ROUTE_2 = SkillRoute(
    skill='search-nex',
    use_when=SkillUseWhen(
        operations=['source discovery for expert retrieval'],
        file_patterns=[],
    ),
    usage_notes=['Auxiliary retrieval support for expert subagents; do not let subagents assign global citation '
 'numbers.'],
)

LAUNCH_EXPERT_SUBAGENTS = StepContract(
    done_when=['expert_results contains one result for every expert in expert_roster.',
 'Every result has a non-empty grounded summary, a distinct artifact, and a new_evidence list.',
 'evidence_registry preserves the persisted prefix and appends any newly retrieved entries with '
 'contiguous citation numbers.',
 'expert_round_index is exactly one greater than the last completed Moderator round.',
 'The complete expert result set is ready for Moderator synthesis.'],
    output_schema={'expert_round_index': 'integer',
 'expert_results': 'object[]',
 'expert_results_complete': 'boolean',
 'evidence_registry': 'string[]'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_expert_ids': 'string[]?'},
    skill_routing=[LAUNCH_EXPERT_SUBAGENTS_ROUTE_1, LAUNCH_EXPERT_SUBAGENTS_ROUTE_2],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.co_storm_autonomous_research.verifiers:verify_launch_expert_subagents",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

AUTONOMOUS_ROUNDTABLE_ROUTE_1 = SkillRoute(
    skill='research-nex',
    use_when=SkillUseWhen(
        operations=['moderated perspective rotation', 'grounded expert turn', 'coverage-driven follow-up research'],
        file_patterns=[],
    ),
    usage_notes=['Primary owner for one autonomous roundtable turn; return one explicit structured decision.'],
)

AUTONOMOUS_ROUNDTABLE = StepContract(
    done_when=['Exactly one new grounded turn is added to the transcript.',
 'The merged evidence registry is carried forward unchanged and topic-level semantic coverage is '
 'updated without dropping prior topic ids.',
 'round_index increases by one and remains within the configured autonomous budget.',
 'round_decision, report_scope_status, coverage_sufficient, and the boolean routing flags are '
 'mutually consistent.',
 'The turn is ready for a continue, reorganize, or report transition.'],
    output_schema={'last_turn_summary': 'string',
 'conversation_transcript': 'string[]',
 'evidence_registry': 'string[]',
 'coverage_map': 'string[]',
 'coverage_assessment': 'object[]',
 'coverage_decision_rationale': 'string',
 'next_round_validation_plan': 'string[]',
 'report_scope_status': 'string',
 'knowledge_map_summary': 'string',
 'expert_roster': 'object[]',
 'round_index': 'integer',
 'round_decision': 'string',
 'continue_roundtable': 'boolean',
 'should_reorganize': 'boolean',
 'coverage_sufficient': 'boolean',
 'ready_for_report': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[AUTONOMOUS_ROUNDTABLE_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.co_storm_autonomous_research.verifiers:verify_autonomous_roundtable",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REORGANIZE_KNOWLEDGE_SPACE_ROUTE_1 = SkillRoute(
    skill='research-nex',
    use_when=SkillUseWhen(
        operations=['knowledge-map expansion', 'topic deduplication', 'coverage-gap extraction'],
        file_patterns=[],
    ),
    usage_notes=['Primary owner for shared knowledge-space maintenance between autonomous rounds.'],
)

REORGANIZE_KNOWLEDGE_SPACE = StepContract(
    done_when=['The knowledge-map summary is materially updated or explicitly confirmed coherent.',
 'Evidence citation identifiers are preserved while redundant or unsupported map branches are '
 'cleaned.',
 'Coverage gaps remain visible for the next roundtable turn.',
 'reorganization_count increases by one.'],
    output_schema={'knowledge_map_summary': 'string',
 'coverage_map': 'string[]',
 'evidence_registry': 'string[]',
 'reorganization_summary': 'string',
 'reorganization_count': 'integer',
 'reorganized': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[REORGANIZE_KNOWLEDGE_SPACE_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.co_storm_autonomous_research.verifiers:verify_reorganize_knowledge_space",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

SYNTHESIZE_REPORT_ROUTE_1 = SkillRoute(
    skill='content-research-writer',
    use_when=SkillUseWhen(
        operations=['evidence-grounded report synthesis',
 'section organization',
 'compact citation and Evidence index formatting'],
        file_patterns=[],
    ),
    usage_notes=['Primary owner for turning the shared knowledge map into the report artifact.',
 'Use number-only [n] markers in the body and a final Evidence index with exact locator-only rows; '
 'do not repeat long locators in prose.'],
)

SYNTHESIZE_REPORT = StepContract(
    done_when=['A report artifact exists.',
 'The report has a clear outline with at least two substantive sections.',
 'Inline numeric citations refer to the carried-forward evidence registry.',
 'The report has exactly one consolidated Evidence index with one exact locator row for every '
 'citation id used in the report body.',
 'Long source locators are not repeated beside body claims.',
 "The report faithfully communicates the Moderator's complete or partial scope decision and "
 'unresolved validation work.',
 'The report is ready for an independent quality and citation gate.'],
    output_schema={'outline': 'string',
 'report_path': 'string',
 'report_summary': 'string',
 'report_sections': 'string[]',
 'report_ready_for_verification': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[SYNTHESIZE_REPORT_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.co_storm_autonomous_research.verifiers:verify_synthesize_report",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

VERIFY_REPORT_ROUTE_1 = SkillRoute(
    skill='content-research-writer',
    use_when=SkillUseWhen(
        operations=['report quality audit', 'citation coverage audit', 'unsupported-claim and duplication detection'],
        file_patterns=[],
    ),
    usage_notes=['Primary owner for the report-quality evidence review; the deterministic verifier code remains '
 'authoritative for routing, and the LLM verdict is advisory input to the repair loop.'],
)

VERIFY_REPORT = StepContract(
    done_when=['The report is read and checked against the evidence registry and coverage map.',
 'quality_verdict is pass only when citation and section gates are satisfied.',
 'The audit confirms that complete reports have sufficient semantic coverage and partial reports '
 'disclose all unresolved coverage work.',
 'Quality findings and the citation coverage summary are recorded.',
 'The report is explicitly marked ready for finalization or repair.',
 'quality_verdict is pass only when the report body uses compact [n] markers and the final '
 'Evidence index satisfies the exact locator mapping.'],
    output_schema={'quality_verdict': 'string',
 'quality_findings': 'string[]',
 'citation_coverage_summary': 'string',
 'report_ready': 'boolean',
 'verified_report_path': 'string'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[VERIFY_REPORT_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.co_storm_autonomous_research.verifiers:verify_verify_report",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REPAIR_REPORT_ROUTE_1 = SkillRoute(
    skill='content-research-writer',
    use_when=SkillUseWhen(
        operations=['citation repair planning', 'section coverage repair', 'grounded report repair planning'],
        file_patterns=[],
    ),
    usage_notes=['Primary owner for report-specific recovery; it prepares the next report pass.'],
)

REPAIR_REPORT = StepContract(
    done_when=['The available audit or repair context is translated into concrete repair actions.',
 'Missing or mismatched Evidence index rows are named when citation findings require them.',
 'The repair handoff is ready for the report synthesis stage.',
 'No unsupported new facts are introduced during repair.'],
    output_schema={'report_repair_summary': 'string', 'repair_actions': 'string[]', 'repair_ready': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[REPAIR_REPORT_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.co_storm_autonomous_research.verifiers:verify_repair_report",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REQUEST_UNBLOCKING_INPUT = StepContract(
    done_when=['Identify the blocking reason',
 'Record a diagnostic for the missing dependency without requesting a user response'],
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
    "warm_start_shared_space": WARM_START_SHARED_SPACE,
    "launch_expert_subagents": LAUNCH_EXPERT_SUBAGENTS,
    "autonomous_roundtable": AUTONOMOUS_ROUNDTABLE,
    "reorganize_knowledge_space": REORGANIZE_KNOWLEDGE_SPACE,
    "synthesize_report": SYNTHESIZE_REPORT,
    "verify_report": VERIFY_REPORT,
    "repair_report": REPAIR_REPORT,
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
