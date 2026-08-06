from __future__ import annotations

from pathlib import Path

from workflows.common.contracts import VerifierResult, make_verifier_result
from workflows.common.policies import condition_matches

def verify_warm_start_shared_space(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'expert_roster': 'object[]',
 'conversation_transcript': 'string[]',
 'knowledge_map_summary': 'string',
 'evidence_registry': 'string[]',
 'coverage_map': 'string[]',
 'round_index': 'integer',
 'warm_start_ready': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'knowledge_map_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Warm start must produce a non-empty shared knowledge-map summary.'},
 {'output_key': 'warm_start_ready',
  'operator': 'is_true',
  'value': None,
  'message': 'Warm start must explicitly declare the shared space ready for roundtable rotation.'},
 {'output_key': 'round_index',
  'operator': 'equals',
  'value': 0,
  'message': 'Warm start must initialize round_index to zero.'}],
        verifier_templates=[{'id': 'warm_start_requires_multiple_experts',
  'template': 'min_count',
  'output_key': 'expert_roster',
  'message': 'Warm start must create at least two expert perspectives.',
  'min_count': 2},
 {'id': 'warm_start_requires_transcript',
  'template': 'min_count',
  'output_key': 'conversation_transcript',
  'message': 'Warm start must contain at least two grounded research turns.',
  'min_count': 2},
 {'id': 'warm_start_requires_evidence',
  'template': 'min_count',
  'output_key': 'evidence_registry',
  'message': 'Warm start must seed at least three traceable evidence entries.',
  'min_count': 3},
 {'id': 'warm_start_requires_coverage_baseline',
  'template': 'min_count',
  'output_key': 'coverage_map',
  'message': 'Warm start must record at least two coverage topics.',
  'min_count': 2}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_warm_start_shared_space(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_launch_expert_subagents(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'execution_mode': 'string',
 'fanout_round_index': 'integer',
 'subagent_expert_ids': 'string[]',
 'subagent_run_ids': 'string[]',
 'subagent_result_summaries': 'string[]',
 'subagent_artifact_paths': 'string[]',
 'subagent_binding_records': 'object[]',
 'fanout_complete': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'execution_mode',
  'operator': 'equals',
  'value': 'parallel_fanout',
  'message': 'Expert subagents must be launched through the parallel fan-out execution mode.'},
 {'output_key': 'fanout_complete',
  'operator': 'is_true',
  'value': None,
  'message': 'The fan-out stage must confirm that every expert subagent completed.'}],
        verifier_templates=[{'id': 'fanout_requires_experts',
  'template': 'min_count',
  'output_key': 'subagent_expert_ids',
  'message': 'Fan-out must return at least two independent expert identifiers.',
  'min_count': 2},
 {'id': 'fanout_requires_run_ids',
  'template': 'min_count',
  'output_key': 'subagent_run_ids',
  'message': 'Fan-out must return independent subagent run identifiers.',
  'min_count': 2},
 {'id': 'fanout_requires_summaries',
  'template': 'min_count',
  'output_key': 'subagent_result_summaries',
  'message': 'Every expert subagent must return a grounded result summary.',
  'min_count': 2},
 {'id': 'fanout_requires_artifacts',
  'template': 'min_count',
  'output_key': 'subagent_artifact_paths',
  'message': 'Every expert subagent must hand in a result artifact path.',
  'min_count': 2}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_launch_expert_subagents(
        output=output,
        state=state,
        repo_root=repo_root,
        tool_trace=observation.get("tool_trace"),
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_autonomous_roundtable(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'last_turn_summary': 'string',
 'conversation_transcript': 'string[]',
 'evidence_registry': 'string[]',
 'coverage_map': 'string[]',
 'knowledge_map_summary': 'string',
 'expert_roster': 'object[]',
 'round_index': 'integer',
 'round_decision': 'string',
 'continue_roundtable': 'boolean',
 'should_reorganize': 'boolean',
 'coverage_sufficient': 'boolean',
 'ready_for_report': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'last_turn_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Each autonomous round must return a non-empty turn summary.'},
 {'output_key': 'round_decision',
  'operator': 'one_of',
  'value': ['continue', 'reorganize', 'report'],
  'message': 'round_decision must be continue, reorganize, or report.'}],
        verifier_templates=[{'id': 'roundtable_requires_evidence',
  'template': 'min_count',
  'output_key': 'evidence_registry',
  'message': 'The roundtable must preserve at least three traceable evidence entries.',
  'min_count': 3},
 {'id': 'roundtable_requires_coverage',
  'template': 'min_count',
  'output_key': 'coverage_map',
  'message': 'The roundtable must preserve at least two coverage topics.',
  'min_count': 2}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_autonomous_roundtable(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_reorganize_knowledge_space(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'knowledge_map_summary': 'string',
 'coverage_map': 'string[]',
 'evidence_registry': 'string[]',
 'reorganization_summary': 'string',
 'reorganization_count': 'integer',
 'reorganized': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'knowledge_map_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Knowledge reorganization must return a non-empty map summary.'},
 {'output_key': 'reorganization_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Knowledge reorganization must explain the structural changes or coherence check.'},
 {'output_key': 'reorganized',
  'operator': 'is_true',
  'value': None,
  'message': 'The reorganization stage must explicitly confirm completion.'}],
        verifier_templates=[{'id': 'reorganization_requires_coverage',
  'template': 'min_count',
  'output_key': 'coverage_map',
  'message': 'Reorganization must preserve at least two visible coverage topics.',
  'min_count': 2},
 {'id': 'reorganization_requires_evidence',
  'template': 'min_count',
  'output_key': 'evidence_registry',
  'message': 'Reorganization must preserve at least three evidence entries.',
  'min_count': 3}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_reorganize_knowledge_space(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_synthesize_report(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'outline': 'string',
 'report_path': 'string',
 'report_summary': 'string',
 'report_sections': 'string[]',
 'report_ready_for_verification': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'outline',
  'operator': 'truthy',
  'value': None,
  'message': 'Report synthesis must return a non-empty outline.'},
 {'output_key': 'report_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'Report synthesis must create the report file before continuing.'},
 {'output_key': 'report_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Report synthesis must return a non-empty report summary.'},
 {'output_key': 'report_ready_for_verification',
  'operator': 'is_true',
  'value': None,
  'message': 'Report synthesis must explicitly hand the artifact to verification.'}],
        verifier_templates=[{'id': 'report_requires_multiple_sections',
  'template': 'min_count',
  'output_key': 'report_sections',
  'message': 'The report must contain at least two substantive sections.',
  'min_count': 2},
 {'id': 'report_file_contains_headings',
  'template': 'artifact_file_contains_sections',
  'output_key': 'report_path',
  'message': 'The report file must contain a title and section headings.',
  'sections': ['#', '##']}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_verify_report(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'quality_verdict': 'string',
 'quality_findings': 'string[]',
 'citation_coverage_summary': 'string',
 'report_ready': 'boolean',
 'verified_report_path': 'string'},
        optional_schema={},
        verifier_rules=[{'output_key': 'quality_verdict',
  'operator': 'one_of',
  'value': ['pass', 'repair'],
  'message': 'quality_verdict must be pass or repair.'},
 {'output_key': 'citation_coverage_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'The report audit must return a citation coverage summary.'},
 {'output_key': 'verified_report_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'The report audit must return an existing report path.'}],
        verifier_templates=[{'id': 'verified_report_contains_headings',
  'template': 'artifact_file_contains_sections',
  'output_key': 'verified_report_path',
  'message': 'The verified report must retain a title and section headings.',
  'sections': ['#', '##']},
 {'id': 'pass_report_requires_ready_flag',
  'template': 'conditional_equals',
  'output_key': 'report_ready',
  'message': 'A pass quality verdict must set report_ready to true.',
  'when': {'output_key': 'quality_verdict', 'operator': 'equals', 'value': 'pass'},
  'expected_value': True}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_verify_report(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_repair_report(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'report_repair_summary': 'string', 'repair_actions': 'string[]', 'repair_ready': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'report_repair_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Report repair must return a non-empty repair summary.'},
 {'output_key': 'repair_ready',
  'operator': 'is_true',
  'value': None,
  'message': 'Report repair must explicitly hand the repair back to synthesis.'}],
        verifier_templates=[{'id': 'report_repair_requires_actions',
  'template': 'min_count',
  'output_key': 'repair_actions',
  'message': 'Report repair must return at least one concrete repair action.',
  'min_count': 1}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def _run_custom_verifier_requirements_warm_start_shared_space(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_warm_start_shared_space_expert_roster_has_stable_identity(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: warm_start_shared_space
# custom_verifier_requirement_id: expert_roster_has_stable_identity
# template_version: 1
# spec_fingerprint: c181413b065524a1534ef02412c374429b21e06d5cb0aff57b77e972271ce374
# implementation_version: 1
def _custom_verifier_requirement_warm_start_shared_space_expert_roster_has_stable_identity(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: The warm-start expert roster must be a structured list of stable expert records; later fan-out bindings reference only each record's id.
Signals: expert_roster
Implementation surfaces: verifiers.py, state.py, workflow-specific regression tests
Hint pseudocode:
- Require expert_roster to be a list of objects with exactly id, role, and brief string fields.
- Require every expert id, role, and brief to be non-empty and every id to be unique.
- Reject legacy string-only roster entries instead of guessing whether a description is a stable identifier.
Test intent:
- Accept two structured expert records with distinct ids.
- Reject a legacy string-only roster entry.
- Reject duplicate or incomplete expert records."""
    from .fanout_contract import parse_expert_roster

    _, errors = parse_expert_roster(output.get("expert_roster"))
    return "; ".join(errors) if errors else None

def _run_custom_verifier_requirements_launch_expert_subagents(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
    tool_trace: object,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_launch_expert_subagents_independent_subagents_complete(
        output=output,
        state=state,
        repo_root=repo_root,
        tool_trace=tool_trace,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: launch_expert_subagents
# custom_verifier_requirement_id: independent_subagents_complete
# template_version: 1
# spec_fingerprint: 5b0c20db5ce718f5fce94650cbdb676cec28461895917aa1f3ac1fd7815ca758
# implementation_version: 2
def _custom_verifier_requirement_launch_expert_subagents_independent_subagents_complete(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
    tool_trace: object,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: The fan-out stage must launch exactly one independent subagent per stable expert identifier, collect all results for one autonomous round, preserve prior run history, and prove that each result is grounded and stored as a safe repository-relative artifact.
Signals: expert_roster, fanout_round_index, subagent_expert_ids, subagent_run_ids, subagent_result_summaries, subagent_artifact_paths, subagent_binding_records, subagent_run_history, execution_mode, tool_trace
Implementation surfaces: verifiers.py, state.py, policy.py, workflow-specific regression tests
Hint pseudocode:
- Require execution_mode to be parallel_fanout and fanout_complete to be true.
- Require persisted state.round_index to be non-negative, require fanout_round_index to be at least one and equal persisted state.round_index + 1, and reject values above constraints.max_rounds.
- Require subagent_expert_ids to equal the persisted expert_roster exactly, with no duplicates or omissions.
- Require subagent_run_ids, summaries, and artifact paths to have the same length as expert_roster; all run IDs, summaries, and paths must be unique and non-empty.
- Require subagent_binding_records to be structured objects whose expert_id, subagent_run_id, summary, and artifact_path fields match the corresponding arrays in order; spawn_receipt must be unique per expert and completion_receipt may be shared only when one real batch join trace covers the same experts and runs.
- Treat persisted subagent_run_history as canonical structured records, reject any reused run ID, and let runtime derive the exact current history tail instead of requiring model-echoed history.
- Resolve every artifact path under repo_root, require a regular readable file with non-empty UTF-8 content, and reject paths outside repo_root.
- Normalize flat and nested trace entries before checking them. Require one successful spawn per expert and exactly one successful join coverage per expert; a batch join may cover several experts with one real receipt and must not be split into synthetic receipts.
- Do not accept a single summary or one reused subagent run ID as evidence for multiple expert perspectives.
Test intent:
- Accept a parallel fan-out with two stable expert IDs, two distinct subagent run IDs, two result summaries, and two readable artifacts.
- Reject a fan-out that reuses one subagent run ID for two experts.
- Reject a fan-out that omits an expert or adds an unknown expert.
- Reject a fan-out with a skipped round, rewritten canonical history, prior run reuse, an artifact alias, or an artifact outside repo_root.
- Reject a fan-out with missing spawn/wait tool traces or binding records that mismatch the parallel arrays."""
    from .fanout_contract import fanout_contract_errors

    errors = fanout_contract_errors(
        output=output,
        state=state,
        repo_root=repo_root,
        tool_trace=tool_trace,
    )
    return "; ".join(errors) if errors else None

def _run_custom_verifier_requirements_autonomous_roundtable(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_autonomous_roundtable_roundtable_flags_match_decision(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: autonomous_roundtable
# custom_verifier_requirement_id: roundtable_flags_match_decision
# template_version: 1
# spec_fingerprint: 65104bbd55e4e39b82b2acd40c7dbc812b484ed07a3cccc83f1239e163ad7236
# implementation_version: 3
def _custom_verifier_requirement_autonomous_roundtable_roundtable_flags_match_decision(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: The autonomous roundtable must select exactly one routing decision, preserve the prior transcript, advance exactly one round, and keep the boolean flags and configured budgets consistent with round_decision.
Signals: round_decision, continue_roundtable, should_reorganize, ready_for_report, subagent_run_ids, fanout_complete
Implementation surfaces: verifiers.py, policy.py, workflow-specific regression tests
Hint pseudocode:
- Count the three decision flags and require exactly one true value.
- Map continue to continue_roundtable, reorganize to should_reorganize, and report to ready_for_report.
- Require output.round_index to equal persisted state.round_index + 1 and require the returned transcript to preserve the persisted transcript as an exact prefix plus one new turn.
- Require persisted fanout_complete to be true and persisted subagent_run_ids to be non-empty before the Moderator can accept a round.
- Require the Moderator to carry forward the persisted structured expert roster exactly; fan-out bindings reference expert ids, while role and brief remain runtime-owned roster data.
- Reject round_index values below one, reject values above constraints.max_rounds, and reject continue or reorganize once max_rounds has been reached.
- When coverage_threshold is supplied, require coverage_map to contain at least that many distinct non-empty topics.
Test intent:
- Accept a continue decision with only continue_roundtable true, a strictly incremented round, and one appended transcript turn.
- Reject ambiguous decisions with two true flags.
- Reject a report decision before coverage_sufficient is true unless max_rounds has been reached.
- Reject a skipped round or a rewritten transcript prefix.
- Reject a Moderator turn that has no completed independent expert-subagent fan-out."""
    from .fanout_contract import parse_expert_roster

    persisted_state = state if isinstance(state, dict) else {}
    errors: list[str] = []

    persisted_roster, persisted_errors = parse_expert_roster(
        persisted_state.get("expert_roster")
    )
    output_roster, output_errors = parse_expert_roster(output.get("expert_roster"))
    errors.extend(persisted_errors)
    errors.extend(output_errors)
    if not persisted_errors and not output_errors and output_roster != persisted_roster:
        errors.append("Moderator must carry forward the persisted expert roster exactly")

    decision = output.get("round_decision")
    flag_names = {
        "continue": "continue_roundtable",
        "reorganize": "should_reorganize",
        "report": "ready_for_report",
    }
    flag_values = {
        name: output.get(name) for name in ("continue_roundtable", "should_reorganize", "ready_for_report")
    }
    if any(not isinstance(value, bool) for value in flag_values.values()):
        errors.append("roundtable decision flags must be booleans")
    true_flags = [name for name, value in flag_values.items() if value is True]
    if len(true_flags) != 1:
        errors.append("exactly one roundtable decision flag must be true")
    elif decision in flag_names and true_flags[0] != flag_names[decision]:
        errors.append(f"roundtable flags do not match round_decision={decision!r}")
    if decision not in flag_names:
        errors.append("round_decision must be continue, reorganize, or report")

    round_index = output.get("round_index")
    previous_round = persisted_state.get("round_index")
    if not isinstance(previous_round, int) or isinstance(previous_round, bool) or previous_round < 0:
        errors.append("persisted state.round_index must be a non-negative integer")
    if not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 1:
        errors.append("round_index must be a positive integer")
    elif isinstance(previous_round, int) and not isinstance(previous_round, bool) and round_index != previous_round + 1:
        errors.append(
            f"round_index expected {previous_round + 1}, actual {round_index}"
        )

    constraints = persisted_state.get("constraints")
    constraints = constraints if isinstance(constraints, dict) else {}
    max_rounds = constraints.get("max_rounds")
    if not isinstance(max_rounds, int) or isinstance(max_rounds, bool) or max_rounds <= 0:
        errors.append("constraints.max_rounds must be a positive integer")
    elif isinstance(round_index, int) and not isinstance(round_index, bool):
        if round_index > max_rounds:
            errors.append(f"round_index {round_index} exceeds max_rounds {max_rounds}")
        if decision in {"continue", "reorganize"} and round_index == max_rounds:
            errors.append("continue or reorganize is not allowed at max_rounds")
        if decision == "report" and output.get("coverage_sufficient") is not True and round_index != max_rounds:
            errors.append("report requires coverage_sufficient unless max_rounds is reached")

    if persisted_state.get("fanout_complete") is not True:
        errors.append("Moderator requires a completed expert fan-out")
    run_ids = persisted_state.get("subagent_run_ids")
    if not isinstance(run_ids, list) or not run_ids:
        errors.append("persisted subagent_run_ids must contain completed independent runs")
    elif any(not isinstance(item, str) or not item.strip() for item in run_ids):
        errors.append("persisted subagent_run_ids must contain non-empty strings")
    elif len(set(run_ids)) != len(run_ids):
        errors.append("persisted subagent_run_ids must be unique")

    previous_transcript = persisted_state.get("conversation_transcript")
    current_transcript = output.get("conversation_transcript")
    if not isinstance(previous_transcript, list):
        errors.append("persisted conversation_transcript must be a list")
    if not isinstance(current_transcript, list):
        errors.append("conversation_transcript must be a list")
    elif isinstance(previous_transcript, list) and (
        len(current_transcript) != len(previous_transcript) + 1
        or current_transcript[: len(previous_transcript)] != previous_transcript
    ):
        errors.append("roundtable must preserve the prior transcript and append exactly one turn")

    coverage_threshold = constraints.get("coverage_threshold")
    coverage_map = output.get("coverage_map")
    if coverage_threshold is not None:
        if not isinstance(coverage_threshold, int) or isinstance(coverage_threshold, bool) or coverage_threshold <= 0:
            errors.append("constraints.coverage_threshold must be a positive integer when supplied")
        elif not isinstance(coverage_map, list):
            errors.append("coverage_map must be a list")
        else:
            topics = [item.strip() for item in coverage_map if isinstance(item, str) and item.strip()]
            if len(set(topics)) < coverage_threshold:
                errors.append(
                    f"coverage_map must contain at least {coverage_threshold} distinct non-empty topics"
                )

    return "; ".join(errors) if errors else None

def _run_custom_verifier_requirements_reorganize_knowledge_space(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_reorganize_knowledge_space_reorganization_budget_is_respected(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: reorganize_knowledge_space
# custom_verifier_requirement_id: reorganization_budget_is_respected
# template_version: 1
# spec_fingerprint: a717cf3d57d0e1a7f0712716bb2da71a120bdbc2857fa7027c3caedcbda5c939
# implementation_version: 2
def _custom_verifier_requirement_reorganize_knowledge_space_reorganization_budget_is_respected(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: Knowledge-space reorganization must advance the counter exactly once, preserve grounded evidence entries, and respect the autonomous reorganization budget.
Signals: reorganization_count, reorganized
Implementation surfaces: verifiers.py, workflow-specific regression tests
Hint pseudocode:
- Require reorganization_count to be an integer greater than zero and exactly one greater than persisted state.reorganization_count.
- Read constraints.max_reorganizations from persisted state and reject counts above that value or a reorganization after the budget is exhausted.
- Reject empty evidence entries and preserve the citation identifiers carried by the prior state.
Test intent:
- Accept the first reorganization when the configured budget is two.
- Reject a reorganization count above the configured budget.
- Reject a reorganization that skips a counter value."""
    import re

    count = output.get("reorganization_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        return "reorganization_count must be a positive integer"
    if output.get("reorganized") is not True:
        return "reorganization must be explicitly marked complete"

    persisted_state = state if isinstance(state, dict) else {}
    previous_count = persisted_state.get("reorganization_count")
    if previous_count is None:
        if count != 1:
            return "the first reorganization must set reorganization_count to one"
    elif (
        not isinstance(previous_count, int)
        or isinstance(previous_count, bool)
        or previous_count < 0
        or count != previous_count + 1
    ):
        return "reorganization_count must advance exactly one step from persisted state"

    constraints = persisted_state.get("constraints")
    constraints = constraints if isinstance(constraints, dict) else {}
    max_reorganizations = constraints.get("max_reorganizations")
    if max_reorganizations is not None:
        if not isinstance(max_reorganizations, int) or isinstance(max_reorganizations, bool) or max_reorganizations < 1:
            return "constraints.max_reorganizations must be a positive integer when supplied"
        if count > max_reorganizations:
            return "reorganization_count exceeds constraints.max_reorganizations"

    evidence_registry = output.get("evidence_registry")
    if not isinstance(evidence_registry, list):
        return "evidence_registry must be a list"
    evidence_ids = set()
    for entry in evidence_registry:
        if not isinstance(entry, str):
            return "evidence_registry entries must be strings"
        match = re.match(r"^\s*\[(\d+)\]\s*(.+?)\s*$", entry)
        if match is None or not match.group(2).strip():
            return "evidence_registry entries must contain a citation identifier and grounded details"
        evidence_id = int(match.group(1))
        if evidence_id in evidence_ids:
            return "evidence_registry contains duplicate citation identifiers"
        evidence_ids.add(evidence_id)

    previous_evidence = persisted_state.get("evidence_registry")
    if isinstance(previous_evidence, list):
        previous_ids = set()
        for entry in previous_evidence:
            if not isinstance(entry, str):
                return "persisted evidence_registry entries must be strings"
            match = re.match(r"^\s*\[(\d+)\]", entry)
            if match is None:
                return "persisted evidence_registry entries must have numeric citation identifiers"
            previous_ids.add(int(match.group(1)))
        if not previous_ids.issubset(evidence_ids):
            return "reorganization must preserve prior evidence citation identifiers"
    return None

def _run_custom_verifier_requirements_verify_report(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_verify_report_report_citation_integrity(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: verify_report
# custom_verifier_requirement_id: report_citation_integrity
# template_version: 1
# spec_fingerprint: 0fd2368125125f36815a5409a5e0ec287f7d722af2ad791540465ea42a10c023
# implementation_version: 2
def _custom_verifier_requirement_verify_report_report_citation_integrity(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: Every numeric inline citation in the report must resolve to a non-empty grounded evidence entry carried in state; repair verdicts must explicitly fail the gate and pass verdicts must satisfy the final quality conditions.
Signals: report_path, verified_report_path, evidence_registry, report_ready, quality_verdict, quality_findings, coverage_map
Implementation surfaces: verifiers.py, workflow-specific regression tests
Hint pseudocode:
- Read the repository-relative report path safely under repo_root.
- Extract numeric markers such as [1] from the report and parse numeric identifiers from evidence_registry entries.
- Reject unknown markers, missing or empty evidence entries, or a pass verdict with no citation markers.
- Require verified_report_path to resolve to the same repository-relative regular file as report_path.
- Reject unresolved critical or blocker findings when quality_verdict is pass, and make a repair verdict fail this verifier so policy enters repair_report.
Test intent:
- Accept a report whose [1] and [2] markers exist in the evidence registry.
- Reject a report containing an unknown [99] marker.
- Reject a pass verdict for an uncited report.
- Reject a pass verdict with an unresolved critical finding.
- Reject a repair verdict as a verifier failure so the repair route is taken."""
    import re

    persisted_state = state if isinstance(state, dict) else {}
    report_path = persisted_state.get("report_path")
    verified_report_path = output.get("verified_report_path")
    if not isinstance(report_path, str) or not report_path.strip():
        return "persisted report_path is missing"
    if not isinstance(verified_report_path, str) or not verified_report_path.strip():
        return "verified_report_path is missing"

    repo = Path(repo_root).resolve()
    resolved_paths = []
    for label, raw_path in (("report_path", report_path), ("verified_report_path", verified_report_path)):
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = repo / candidate
        try:
            resolved = candidate.resolve()
            resolved.relative_to(repo)
        except (OSError, ValueError):
            return f"{label} must resolve inside repo_root"
        if not resolved.is_file():
            return f"{label} must point to a readable report file"
        resolved_paths.append(resolved)
    if resolved_paths[0] != resolved_paths[1]:
        return "verified_report_path must identify the same artifact as persisted report_path"

    try:
        report_text = resolved_paths[0].read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "report file could not be read as UTF-8"

    markers = {int(value) for value in re.findall(r"\[(\d+)\]", report_text)}
    if not markers:
        return "report must contain at least one numeric inline citation"

    evidence_registry = persisted_state.get("evidence_registry")
    if not isinstance(evidence_registry, list) or not evidence_registry:
        return "evidence_registry is missing from persisted state"
    evidence_ids = set()
    for entry in evidence_registry:
        if not isinstance(entry, str):
            return "evidence_registry entries must be strings"
        match = re.match(r"^\s*\[(\d+)\]\s*(.+?)\s*$", entry)
        if match is None or not match.group(2).strip():
            return "every evidence_registry entry must contain a citation identifier and grounded details"
        evidence_id = int(match.group(1))
        if evidence_id in evidence_ids:
            return "evidence_registry contains duplicate citation identifiers"
        evidence_ids.add(evidence_id)

    unknown_markers = sorted(markers - evidence_ids)
    if unknown_markers:
        return f"report contains citation identifiers absent from evidence_registry: {unknown_markers}"

    quality_verdict = output.get("quality_verdict")
    report_ready = output.get("report_ready")
    if quality_verdict == "repair":
        if report_ready is not False:
            return "a repair quality verdict must set report_ready to false"
        return "quality verifier requested report repair"
    if quality_verdict == "pass":
        if report_ready is not True:
            return "a pass quality verdict requires report_ready to be true"
        findings = output.get("quality_findings") or []
        if any(
            isinstance(finding, str)
            and re.match(r"^\s*(critical|blocker|p0)(?:\b|:)", finding, re.IGNORECASE)
            and not re.search(r"\b(resolved|fixed|closed)\b", finding, re.IGNORECASE)
            for finding in findings
        ):
            return "a pass quality verdict cannot contain unresolved critical or blocker findings"
    return None

def _verify_structured_output_schema(
    *,
    run_id: str,
    step_id: str,
    required_schema: dict[str, str],
    optional_schema: dict[str, str],
    verifier_rules: list[dict],
    verifier_templates: list[dict],
    observation: dict,
    repo_root: str,
    state: dict | None,
) -> VerifierResult:
    output = observation.get("structured_output")
    if output is None:
        output = {}
    if not isinstance(output, dict):
        return _fail("structured_output must be an object", run_id, step_id, state)
    missing = [key for key in required_schema if key not in output]
    if missing:
        return _fail(f"missing required structured_output keys: {missing}", run_id, step_id, state)
    schema_errors = []
    for key, schema_type in required_schema.items():
        message = _schema_type_error(key, output.get(key), schema_type, required=True)
        if message:
            schema_errors.append(message)
    for key, schema_type in optional_schema.items():
        if key in output:
            message = _schema_type_error(key, output.get(key), schema_type, required=False)
            if message:
                schema_errors.append(message)
    if schema_errors:
        return _fail("; ".join(schema_errors), run_id, step_id, state)
    rule_errors = []
    for rule in verifier_rules:
        message = _verifier_rule_error(rule, output, repo_root)
        if message:
            rule_errors.append(message)
    if rule_errors:
        return _fail("; ".join(rule_errors), run_id, step_id, state)
    template_errors = []
    for template in verifier_templates:
        message = _verifier_template_error(template, output, repo_root)
        if message:
            template_errors.append(message)
    if template_errors:
        return _fail("; ".join(template_errors), run_id, step_id, state)
    return make_verifier_result(
        passed=True,
        message="structured_output schema, verifier rules, and verifier templates are satisfied",
        details={
            "run_id": run_id,
            "step_id": step_id,
            "checked_required_keys": sorted(required_schema),
            "checked_optional_keys": sorted(optional_schema),
        },
    )


def _schema_type_error(
    key: str,
    value: object,
    schema_type: str,
    *,
    required: bool,
) -> str | None:
    normalized = schema_type.rstrip("?")
    if value is None and not required:
        return None
    if normalized == "string":
        if not isinstance(value, str):
            return f"{key} must be a string"
        if required and not value.strip():
            return f"{key} must be a non-empty string"
        return None
    if normalized == "boolean":
        if not isinstance(value, bool):
            return f"{key} must be a boolean"
        return None
    if normalized == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return f"{key} must be an integer"
        return None
    if normalized == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"{key} must be a number"
        return None
    if normalized == "object":
        if not isinstance(value, dict):
            return f"{key} must be an object"
        return None
    if normalized.endswith("[]"):
        if not isinstance(value, list):
            return f"{key} must be a list"
        item_type = normalized[:-2]
        for index, item in enumerate(value):
            message = _schema_type_error(f"{key}[{index}]", item, item_type, required=False)
            if message:
                return message
        return None
    return None


def _verifier_rule_error(rule: dict, output: dict, repo_root: str) -> str | None:
    key = str(rule.get("output_key") or "")
    operator = str(rule.get("operator") or "")
    expected = rule.get("value")
    message = str(rule.get("message") or f"{key} failed verifier rule: {operator}")
    actual = output.get(key)
    if operator == "one_of":
        allowed = expected if isinstance(expected, list) else []
        return None if actual in allowed else message
    if operator == "path_exists":
        if not isinstance(actual, str) or not actual.strip():
            return message
        candidate = Path(actual)
        repo = Path(repo_root).resolve()
        if not candidate.is_absolute():
            candidate = repo / candidate
        try:
            candidate = candidate.resolve()
            candidate.relative_to(repo)
        except (OSError, ValueError):
            return message
        return None if candidate.is_file() else message
    return None if condition_matches(actual, operator, expected) else message


def _verifier_template_error(template: dict, output: dict, repo_root: str) -> str | None:
    template_name = str(template.get("template") or "")
    message = str(template.get("message") or f"{template.get('id') or template_name} failed")
    key = str(template.get("output_key") or "")
    actual = output.get(key)
    if template_name == "conditional_equals":
        return _conditional_equals_error(actual, output, template, message)
    if template_name == "conditional_required":
        return _conditional_required_error(output, template, message)
    if template_name == "min_count":
        return _min_count_error(actual, template, message)
    if template_name == "required_set_members":
        return _required_set_members_error(actual, template, message)
    if template_name == "repo_path_policy":
        return _repo_path_policy_error(actual, template, repo_root, message)
    if template_name == "artifact_file_contains_sections":
        return _artifact_file_contains_sections_error(actual, template, repo_root, message)
    return message


def _conditional_required_error(output: dict, template: dict, message: str) -> str | None:
    when = template.get("when") or {}
    if not isinstance(when, dict):
        return message
    when_key = str(when.get("output_key") or "")
    if not condition_matches(output.get(when_key), str(when.get("operator") or ""), when.get("value")):
        return None
    required_key = str(template.get("required_key") or "")
    return None if output.get(required_key) else message


def _conditional_equals_error(actual, output: dict, template: dict, message: str) -> str | None:
    when = template.get("when") or {}
    if not isinstance(when, dict):
        return message
    when_key = str(when.get("output_key") or "")
    if not condition_matches(output.get(when_key), str(when.get("operator") or ""), when.get("value")):
        return None
    return None if actual == template.get("expected_value") else message


def _min_count_error(actual, template: dict, message: str) -> str | None:
    if not isinstance(actual, list):
        return message
    min_count = template.get("min_count")
    if not isinstance(min_count, int) or isinstance(min_count, bool):
        return message
    return None if len(actual) >= min_count else message


def _required_set_members_error(actual, template: dict, message: str) -> str | None:
    if not isinstance(actual, list):
        return message
    required = template.get("required_members")
    if not isinstance(required, list):
        return message
    case_sensitive = bool(template.get("case_sensitive", False))
    if case_sensitive:
        normalized = {str(item).strip() for item in actual if str(item).strip()}
        required_members = {str(item).strip() for item in required if str(item).strip()}
    else:
        normalized = {str(item).strip().lower() for item in actual if str(item).strip()}
        required_members = {str(item).strip().lower() for item in required if str(item).strip()}
    missing = sorted(required_members - normalized)
    return None if not missing else f"{message}: missing members {missing}"


def _repo_path_policy_error(actual, template: dict, repo_root: str, message: str) -> str | None:
    if not isinstance(actual, str) or not actual.strip():
        return message
    repo = Path(repo_root).resolve()
    candidate = Path(actual)
    if not candidate.is_absolute():
        candidate = repo / candidate
    try:
        relative_path = candidate.resolve().relative_to(repo)
    except ValueError:
        return message
    relative_posix = relative_path.as_posix()
    required_prefix = str(template.get("required_prefix") or "")
    if required_prefix and not relative_posix.startswith(required_prefix):
        return message
    forbidden_prefixes = [str(prefix) for prefix in template.get("forbidden_prefixes") or []]
    if any(relative_posix.startswith(prefix) for prefix in forbidden_prefixes):
        return message
    suffix = template.get("required_suffix")
    if isinstance(suffix, str) and suffix and not relative_posix.endswith(suffix):
        return message
    return None


def _artifact_file_contains_sections_error(actual, template: dict, repo_root: str, message: str) -> str | None:
    if not isinstance(actual, str) or not actual.strip():
        return message
    repo = Path(repo_root).resolve()
    candidate = Path(actual)
    if not candidate.is_absolute():
        candidate = repo / candidate
    try:
        candidate = candidate.resolve()
        candidate.relative_to(repo)
        if not candidate.is_file():
            return message
        text = candidate.read_text(encoding="utf-8")
    except (OSError, ValueError, UnicodeError):
        return message
    sections = [str(section) for section in template.get("sections") or []]
    missing = [section for section in sections if section not in text]
    return None if not missing else f"{message}: missing sections {missing}"


def _meaningful_entries(value) -> list[str]:
    if not isinstance(value, list):
        return []
    entries: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            entries.append(text)
    return entries


def _path_has_prefix(path: Path, prefix: Path) -> bool:
    try:
        normalized_path = path.as_posix().strip("/")
        normalized_prefix = prefix.as_posix().strip("/")
    except Exception:
        return False
    return normalized_path == normalized_prefix or normalized_path.startswith(normalized_prefix + "/")


def _extract_single_review_perspective(text: str) -> str | None:
    lowered = str(text).lower()
    matched = [label for label in ("development", "design", "testing") if label in lowered]
    if len(matched) != 1:
        return None
    return matched[0]


def _looks_like_visual_evidence(text: str) -> bool:
    lowered = str(text).lower()
    markers = (
        "visual diff",
        "screenshot diff",
        "screenshot comparison",
        "design comparison",
        "figma",
        "pixel diff",
        "visual qa",
        "mock comparison",
    )
    return any(marker in lowered for marker in markers)


def _has_explicit_severity_prefix(text: str) -> bool:
    return _extract_severity_prefix(text) is not None


def _extract_severity_prefix(text: str) -> str | None:
    normalized = str(text).strip().lower()
    for prefix in ("critical", "blocker", "p0", "important", "high", "p1", "major", "medium", "minor", "low"):
        if normalized.startswith(prefix + ":"):
            return prefix
    return None


def _severity_rank(severity: str) -> int:
    ranks = {
        "critical": 0,
        "blocker": 0,
        "p0": 0,
        "important": 1,
        "high": 1,
        "p1": 1,
        "major": 2,
        "medium": 3,
        "minor": 4,
        "low": 5,
    }
    return ranks.get(severity, 999)


def _fail(message: str, run_id: str, step_id: str, state: dict | None) -> VerifierResult:
    return make_verifier_result(
        passed=False,
        message=message,
        details={"run_id": run_id, "step_id": step_id, "state": state or {}},
    )
