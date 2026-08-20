from workflows.common.contracts import (SkillRoute, SkillUseWhen, StepContract, StepVerifier, WorkflowInputContract)


WORKFLOW_ID = 'earnings_reviewer'

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={'ticker': 'string?', 'reporting_period': 'string?', 'goal': 'string?', 'skip_note': 'boolean?'},
    context_schema={'repo_root': 'string',
 'coverage_model_path': 'string?',
 'transcript_path': 'string?',
 'filings_path': 'string?'},
    constraints_schema={'max_steps': 'integer?'},
)

COLLECT_EARNINGS_PACKET_ROUTE_1 = SkillRoute(
    skill='earnings-reviewer',
    use_when=SkillUseWhen(
        operations=['earnings packet intake', 'actuals and consensus pull', 'transcript and filing collection'],
        file_patterns=['out/**'],
    ),
    usage_notes=['Supporting owner for earnings-reviewer MCP/connectors during packet intake; do not invoke '
 '/earnings-analysis in this stage.',
 'Use FactSet or Daloopa when live market data is available; otherwise use supplied local packet '
 'files.'],
)

COLLECT_EARNINGS_PACKET = StepContract(
    done_when=['Reported actuals, consensus, filings inventory, and the full transcript locator are recorded.',
 'The earnings packet path is recorded under out/.',
 'skip_note is echoed as a boolean.',
 'The packet is ready for call analysis.'],
    output_schema={'ticker': 'string',
 'reporting_period': 'string',
 'earnings_packet_path': 'string',
 'transcript_locator': 'string?',
 'filings_inventory': 'string[]',
 'actuals_source': 'string',
 'consensus_source': 'string',
 'skip_note': 'boolean',
 'missing_packet_inputs': 'string[]',
 'packet_ready': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[COLLECT_EARNINGS_PACKET_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.earnings_reviewer.verifiers:verify_collect_earnings_packet",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

ANALYZE_EARNINGS_CALL_ROUTE_1 = SkillRoute(
    skill='earnings-analysis',
    use_when=SkillUseWhen(
        operations=['earnings call analysis', 'beat/miss and guidance extraction', 'thesis impact assessment'],
        file_patterns=['out/**'],
    ),
    usage_notes=['Primary owner for /earnings-analysis call analysis after the packet exists.'],
)

ANALYZE_EARNINGS_CALL = StepContract(
    done_when=['Headline read, beat/miss summary, guidance changes, tone, and dodged questions are recorded.',
 'Thesis impact is recorded.',
 'The call analysis is ready for the coverage-model update.'],
    output_schema={'headline_read': 'string',
 'beat_miss_summary': 'string',
 'guidance_changes': 'string[]',
 'management_tone': 'string',
 'dodged_questions': 'string[]',
 'thesis_impact': 'string',
 'call_analysis_summary': 'string',
 'unsourced_flags': 'string[]',
 'call_analysis_ready': 'boolean',
 'used_full_transcript': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[ANALYZE_EARNINGS_CALL_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.earnings_reviewer.verifiers:verify_analyze_earnings_call",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

UPDATE_COVERAGE_MODEL_ROUTE_1 = SkillRoute(
    skill='model-update',
    use_when=SkillUseWhen(
        operations=['coverage model update', 'estimate revision', 'variance table construction'],
        file_patterns=['out/**/*.xlsx'],
    ),
    usage_notes=['Primary owner for /model-update after call analysis is complete.'],
)

UPDATE_COVERAGE_MODEL = StepContract(
    done_when=['The updated coverage model path is recorded under out/.',
 'The variance table covers Revenue, GM, EBITDA, and EPS versus consensus and prior estimate.',
 'Estimate changes and thesis-change/handoff flags are recorded.',
 'skip_note is echoed.'],
    output_schema={'updated_model_path': 'string',
 'variance_metrics': 'string[]',
 'variance_rows': 'object[]',
 'estimate_change_summary': 'string',
 'price_target_change': 'string',
 'thesis_change_summary': 'string',
 'requires_model_builder_handoff': 'boolean',
 'skip_note': 'boolean',
 'model_update_ready': 'boolean',
 'handoff_target': 'string?',
 'handoff_reason': 'string?',
 'handoff_payload': 'object?'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[UPDATE_COVERAGE_MODEL_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.earnings_reviewer.verifiers:verify_update_coverage_model",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

AUDIT_COVERAGE_MODEL_ROUTE_1 = SkillRoute(
    skill='audit-xls',
    use_when=SkillUseWhen(
        operations=['excel model audit', 'balance checks', 'hardcode detection'],
        file_patterns=['out/**/*.xlsx'],
    ),
    usage_notes=['Primary owner for /audit-xls at model scope after the coverage model is updated.'],
)

AUDIT_COVERAGE_MODEL = StepContract(
    done_when=['A model-scope audit summary is recorded.',
 'Critical findings are absent or marked resolved.',
 'skip_note is echoed.',
 'The model is ready for note drafting or final staging.'],
    output_schema={'audit_summary': 'string',
 'audit_findings': 'string[]',
 'critical_finding_count': 'integer',
 'skip_note': 'boolean',
 'model_audit_ready': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[AUDIT_COVERAGE_MODEL_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.earnings_reviewer.verifiers:verify_audit_coverage_model",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REPAIR_MODEL_AUDIT_ROUTE_1 = SkillRoute(
    skill='audit-xls',
    use_when=SkillUseWhen(
        operations=['excel model repair', 'audit finding remediation'],
        file_patterns=['out/**/*.xlsx'],
    ),
    usage_notes=['Primary owner for repairing /audit-xls findings before the audit is re-run.'],
)

REPAIR_MODEL_AUDIT = StepContract(
    done_when=['Repair actions against the recorded audit findings are listed.',
 'The coverage model can be re-audited.'],
    output_schema={'repair_summary': 'string', 'repair_actions': 'string[]'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[REPAIR_MODEL_AUDIT_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.earnings_reviewer.verifiers:verify_repair_model_audit",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

DRAFT_EARNINGS_NOTE_ROUTE_1 = SkillRoute(
    skill='morning-note',
    use_when=SkillUseWhen(
        operations=['post-earnings note draft', 'variance table narration', 'staged research draft'],
        file_patterns=['out/**/*.md', 'out/**/*.docx'],
    ),
    usage_notes=['Primary owner for /morning-note after the coverage model has passed audit.'],
)

DRAFT_EARNINGS_NOTE = StepContract(
    done_when=['The staged note path is recorded under out/.',
 'The note headline and variance table are present.',
 'published_externally is false.'],
    output_schema={'note_path': 'string',
 'note_headline': 'string',
 'note_includes_variance_table': 'boolean',
 'published_externally': 'boolean',
 'note_ready': 'boolean'},
    failure_schema={'blocked_reason': 'string?', 'error_message': 'string?', 'missing_inputs': 'string[]?'},
    skill_routing=[DRAFT_EARNINGS_NOTE_ROUTE_1],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.earnings_reviewer.verifiers:verify_draft_earnings_note",
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
    "collect_earnings_packet": COLLECT_EARNINGS_PACKET,
    "analyze_earnings_call": ANALYZE_EARNINGS_CALL,
    "update_coverage_model": UPDATE_COVERAGE_MODEL,
    "audit_coverage_model": AUDIT_COVERAGE_MODEL,
    "repair_model_audit": REPAIR_MODEL_AUDIT,
    "draft_earnings_note": DRAFT_EARNINGS_NOTE,
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
