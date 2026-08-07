from __future__ import annotations

import os
import re

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
  'template': 'min_count_from_constraint',
  'output_key': 'evidence_registry',
  'message': 'Warm start must seed the configured number of traceable evidence entries.',
  'constraint_key': 'min_evidence_items',
  'default_min_count': 3},
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
        required_schema={'expert_round_index': 'integer',
 'expert_results': 'object[]',
 'expert_results_complete': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'expert_results_complete',
  'operator': 'is_true',
  'value': None,
  'message': 'The expert-result stage must confirm that every expert result is complete.'}],
        verifier_templates=[{'id': 'expert_results_require_multiple_experts',
  'template': 'min_count',
  'output_key': 'expert_results',
  'message': 'The stage must return at least two independent expert results.',
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
  'template': 'min_count_from_constraint',
  'output_key': 'evidence_registry',
  'message': 'The roundtable must preserve the configured number of traceable evidence entries.',
  'constraint_key': 'min_evidence_items',
  'default_min_count': 3},
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
  'template': 'min_count_from_constraint',
  'output_key': 'evidence_registry',
  'message': 'Reorganization must preserve the configured number of evidence entries.',
  'constraint_key': 'min_evidence_items',
  'default_min_count': 3}],
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

def _run_custom_verifier_requirements_launch_expert_subagents(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_launch_expert_subagents_expert_results_match_roster(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: launch_expert_subagents
# custom_verifier_requirement_id: expert_results_match_roster
# template_version: 1
# spec_fingerprint: 91d85e24740693b5266cad0d48cf2c55cd8853d2fc6712c33bcd929534ec4415
# implementation_version: 3
def _custom_verifier_requirement_launch_expert_subagents_expert_results_match_roster(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Validate exact roster-matched, evidence-grounded expert artifacts."""
    persisted_state = state if isinstance(state, dict) else {}
    errors: list[str] = []
    if output.get("expert_results_complete") is not True:
        errors.append("expert_results_complete must be true")

    roster = persisted_state.get("expert_roster")
    expected_ids: list[str] = []
    if not isinstance(roster, list) or not roster:
        errors.append("persisted expert_roster must contain at least one expert record")
    else:
        for index, expert in enumerate(roster):
            if not isinstance(expert, dict):
                errors.append(f"expert_roster[{index}] must be an object")
                continue
            if set(expert) != {"id", "role", "brief"}:
                errors.append(f"expert_roster[{index}] must contain exactly id, role, and brief")
            expert_id = expert.get("id")
            if not isinstance(expert_id, str) or not expert_id.strip():
                errors.append(f"expert_roster[{index}].id must be a non-empty string")
                continue
            for field_name in ("role", "brief"):
                value = expert.get(field_name)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"expert_roster[{index}].{field_name} must be a non-empty string")
            normalized_id = expert_id.strip()
            if normalized_id in expected_ids:
                errors.append(f"expert_roster contains duplicate id {normalized_id!r}")
            else:
                expected_ids.append(normalized_id)

    previous_round = persisted_state.get("round_index")
    round_index = output.get("expert_round_index")
    if not isinstance(previous_round, int) or isinstance(previous_round, bool) or previous_round < 0:
        errors.append("persisted state.round_index must be a non-negative integer")
    if not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 1:
        errors.append("expert_round_index must be a positive integer")
    elif isinstance(previous_round, int) and not isinstance(previous_round, bool) and round_index != previous_round + 1:
        errors.append(f"expert_round_index expected {previous_round + 1}, actual {round_index}")

    constraints = persisted_state.get("constraints")
    constraints = constraints if isinstance(constraints, dict) else {}
    max_rounds = constraints.get("max_rounds")
    if not isinstance(max_rounds, int) or isinstance(max_rounds, bool) or max_rounds <= 0:
        errors.append("constraints.max_rounds must be a positive integer")
    elif isinstance(round_index, int) and not isinstance(round_index, bool) and round_index > max_rounds:
        errors.append(f"expert_round_index {round_index} exceeds max_rounds {max_rounds}")

    evidence_registry = persisted_state.get("evidence_registry")
    evidence_ids: set[int] = set()
    if not isinstance(evidence_registry, list) or not evidence_registry:
        errors.append("persisted evidence_registry must contain grounded entries")
    else:
        for index, entry in enumerate(evidence_registry):
            if not isinstance(entry, str):
                errors.append(f"evidence_registry[{index}] must be a string")
                continue
            match = re.match(r"^\s*\[(\d+)\]\s*(.+?)\s*$", entry)
            if match is None:
                errors.append(f"evidence_registry[{index}] must contain a citation identifier and claim")
                continue
            evidence_id = int(match.group(1))
            if evidence_id in evidence_ids:
                errors.append(f"evidence_registry contains duplicate citation identifier {evidence_id}")
            evidence_ids.add(evidence_id)

    results = output.get("expert_results")
    if not isinstance(results, list):
        errors.append("expert_results must be a list")
    elif len(results) != len(expected_ids):
        errors.append(f"expert_results must contain exactly {len(expected_ids)} results, actual {len(results)}")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    if isinstance(results, list):
        for index, result in enumerate(results):
            if not isinstance(result, dict):
                errors.append(f"expert_results[{index}] must be an object")
                continue
            if set(result) != {"expert_id", "summary", "artifact_path"}:
                errors.append(f"expert_results[{index}] must contain exactly expert_id, summary, and artifact_path")
                continue
            expert_id = result.get("expert_id")
            summary = result.get("summary")
            artifact_path = result.get("artifact_path")
            if not isinstance(expert_id, str) or not expert_id.strip():
                errors.append(f"expert_results[{index}].expert_id must be a non-empty string")
            else:
                expert_id = expert_id.strip()
                if expert_id in seen_ids:
                    errors.append(f"expert_results contains duplicate expert_id {expert_id!r}")
                seen_ids.add(expert_id)
                if index < len(expected_ids) and expert_id != expected_ids[index]:
                    errors.append(f"expert_results[{index}].expert_id must be {expected_ids[index]!r}, actual {expert_id!r}")
                elif expert_id not in expected_ids:
                    errors.append(f"expert_results contains unknown expert_id {expert_id!r}")
            if not isinstance(summary, str) or not summary.strip():
                errors.append(f"expert_results[{index}].summary must be a non-empty string")
            elif evidence_ids:
                summary_ids = {int(value) for value in re.findall(r"\[(\d+)\]", summary)}
                if not summary_ids.intersection(evidence_ids) or summary_ids - evidence_ids:
                    errors.append(f"expert_results[{index}].summary must cite only registered evidence entries")
            if not isinstance(artifact_path, str) or not artifact_path.strip():
                errors.append(f"expert_results[{index}].artifact_path must be a non-empty string")
                continue
            artifact_path = artifact_path.strip()
            if artifact_path in seen_paths:
                errors.append(f"expert_results contains duplicate artifact_path {artifact_path!r}")
            seen_paths.add(artifact_path)
            if (
                artifact_path.startswith("/")
                or "\\" in artifact_path
                or any(ord(char) < 32 for char in artifact_path)
                or any(part in ("", ".", "..") for part in artifact_path.split("/"))
                or re.match(r"^[A-Za-z]:/", artifact_path)
            ):
                errors.append(f"expert_results[{index}].artifact_path is not repository-relative")
                continue
            try:
                repository = Path(repo_root).expanduser().resolve()
                lexical_path = repository
                for part in artifact_path.split("/"):
                    lexical_path = lexical_path / part
                    if lexical_path.is_symlink():
                        raise ValueError("symlink")
                candidate = repository.joinpath(*artifact_path.split("/"))
                resolved = candidate.resolve(strict=False)
                resolved.relative_to(repository)
                if not resolved.is_file() or resolved.is_symlink() or resolved.stat().st_size <= 0:
                    raise ValueError("not a non-empty regular file")
                with resolved.open("rb") as handle:
                    data = handle.read(_MAX_SAFE_REPO_TEXT_BYTES + 1)
                if len(data) > _MAX_SAFE_REPO_TEXT_BYTES:
                    raise ValueError("artifact is too large")
                artifact_text = data.decode("utf-8")
                if evidence_ids:
                    artifact_ids = {int(value) for value in re.findall(r"\[(\d+)\]", artifact_text)}
                    if not artifact_ids.intersection(evidence_ids) or artifact_ids - evidence_ids:
                        errors.append(f"expert_results[{index}].artifact_path must contain only registered evidence citations")
            except (OSError, UnicodeError, RuntimeError, ValueError):
                errors.append(f"expert_results[{index}].artifact_path must identify a safe, bounded UTF-8 repository file")
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
# spec_fingerprint: e9cd8c49d53369a2002e309a0872a9c7b2bb2c79e073f8d1c2c7804996a234ca
# implementation_version: 4
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

Requirement: The autonomous roundtable must select exactly one routing decision, preserve the prior transcript, advance exactly one round, and require a completed expert-result package.
Signals: round_decision, continue_roundtable, should_reorganize, ready_for_report, expert_results, expert_results_complete
Implementation surfaces: verifiers.py, policy.py, workflow-specific regression tests
Hint pseudocode:
- Count the three decision flags and require exactly one true value.
- Map continue to continue_roundtable, reorganize to should_reorganize, and report to ready_for_report.
- Require output.round_index to equal persisted state.round_index + 1 and require the returned transcript to preserve the persisted transcript as an exact prefix plus one new turn.
- Require persisted expert_results_complete to be true and persisted expert_results to be non-empty before the Moderator can accept a round.
- Require the Moderator to carry forward the persisted structured expert roster exactly.
- Reject round_index values below one, reject values above constraints.max_rounds, and reject continue or reorganize once max_rounds has been reached.
- When coverage_threshold is supplied, require coverage_map to contain at least that many distinct non-empty topics.
Test intent:
- Accept a continue decision with only continue_roundtable true, a strictly incremented round, and one appended transcript turn.
- Reject ambiguous decisions with two true flags.
- Reject a report decision before coverage_sufficient is true unless max_rounds has been reached.
- Reject a skipped round or a rewritten transcript prefix.
- Reject a Moderator turn that has no completed expert-result package."""
    persisted_state = state if isinstance(state, dict) else {}
    errors: list[str] = []

    decision_to_flag = {
        "continue": "continue_roundtable",
        "reorganize": "should_reorganize",
        "report": "ready_for_report",
    }
    flag_names = tuple(decision_to_flag.values())
    flag_values = {name: output.get(name) for name in flag_names}
    if any(not isinstance(value, bool) for value in flag_values.values()):
        errors.append("roundtable decision flags must be booleans")
    true_flags = [name for name, value in flag_values.items() if value is True]
    if len(true_flags) != 1:
        errors.append("exactly one roundtable decision flag must be true")
    decision = output.get("round_decision")
    if decision not in decision_to_flag:
        errors.append("round_decision must be continue, reorganize, or report")
    elif len(true_flags) == 1 and true_flags[0] != decision_to_flag[decision]:
        errors.append(f"roundtable flags do not match round_decision={decision!r}")

    previous_round = persisted_state.get("round_index")
    round_index = output.get("round_index")
    if not isinstance(previous_round, int) or isinstance(previous_round, bool) or previous_round < 0:
        errors.append("persisted state.round_index must be a non-negative integer")
    if not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 1:
        errors.append("round_index must be a positive integer")
    elif isinstance(previous_round, int) and not isinstance(previous_round, bool):
        if round_index != previous_round + 1:
            errors.append(f"round_index expected {previous_round + 1}, actual {round_index}")

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

    if persisted_state.get("expert_results_complete") is not True:
        errors.append("Moderator requires a completed expert-result package")
    expert_results = persisted_state.get("expert_results")
    if not isinstance(expert_results, list) or not expert_results:
        errors.append("persisted expert_results must contain completed results")

    if output.get("expert_roster") != persisted_state.get("expert_roster"):
        errors.append("Moderator must carry forward the persisted expert roster exactly")

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

    resolved_paths = []
    for label, raw_path in (("report_path", report_path), ("verified_report_path", verified_report_path)):
        resolved = _safe_repo_file(repo_root, raw_path)
        if resolved is None:
            return f"{label} must point to a readable repository-relative regular report file"
        resolved_paths.append(resolved)
    if resolved_paths[0] != resolved_paths[1]:
        return "verified_report_path must identify the same artifact as persisted report_path"

    report_text = _read_safe_repo_text(repo_root, report_path)
    if report_text is None:
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
            and re.search(r"\b(critical|blocker|p0)\b", finding, re.IGNORECASE)
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
        message = _verifier_template_error(template, output, repo_root, state)
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
        return None if _safe_repo_file(repo_root, actual) is not None else message
    return None if condition_matches(actual, operator, expected) else message


def _verifier_template_error(template: dict, output: dict, repo_root: str, state: dict | None) -> str | None:
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
    if template_name == "min_count_from_constraint":
        return _min_count_from_constraint_error(actual, template, state, message)
    if template_name == "required_set_members":
        return _required_set_members_error(actual, template, message)
    if template_name == "artifact_list_policy":
        return _artifact_list_policy_error(actual, template, repo_root, message)
    if template_name == "no_unresolved_findings":
        return _no_unresolved_findings_error(output, template, message)
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
    if len(actual) < min_count:
        return message
    if any(isinstance(item, str) and not item.strip() for item in actual):
        return message
    return None


def _min_count_from_constraint_error(actual, template: dict, state: dict | None, message: str) -> str | None:
    if not isinstance(actual, list):
        return message
    constraints = state.get("constraints") if isinstance(state, dict) else {}
    constraint_key = str(template.get("constraint_key") or "")
    raw_min_count = constraints.get(constraint_key) if isinstance(constraints, dict) else None
    default_min_count = template.get("default_min_count")
    min_count = raw_min_count if isinstance(raw_min_count, int) and not isinstance(raw_min_count, bool) and raw_min_count >= 0 else default_min_count
    if not isinstance(min_count, int) or isinstance(min_count, bool) or min_count < 0:
        return message
    if len(actual) < min_count:
        return message
    if any(isinstance(item, str) and not item.strip() for item in actual):
        return message
    return None


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
    candidate = _safe_repo_path(repo_root, actual)
    if candidate is None:
        return message
    repo = Path(repo_root).expanduser().resolve()
    relative_path = candidate.relative_to(repo)
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
    if _safe_repo_file(repo_root, actual) is None:
        return message
    text = _read_safe_repo_text(repo_root, actual)
    if text is None or not text.strip():
        return message
    sections = [str(section) for section in template.get("sections") or []]
    missing = []
    for section in sections:
        if section.startswith("#") and set(section) == {"#"}:
            pattern = rf"(?m)^\s*{re.escape(section)}(?!#)\s+\S"
            if re.search(pattern, text) is None:
                missing.append(section)
        elif section not in text:
            missing.append(section)
    return None if not missing else f"{message}: missing sections {missing}"


def _artifact_list_policy_error(actual, template: dict, repo_root: str, message: str) -> str | None:
    if not isinstance(actual, list) or not actual:
        return message
    required_prefix = str(template.get("required_prefix") or "")
    allowed_suffixes = tuple(str(item).lower() for item in template.get("allowed_suffixes") or [])
    require_non_empty_content = bool(template.get("require_non_empty_content", True))
    for index, item in enumerate(actual):
        if not isinstance(item, str) or not item.strip():
            return f"{message}: invalid artifact at index {index}"
        candidate = _safe_repo_file(repo_root, item)
        if candidate is None:
            return f"{message}: invalid artifact at index {index}"
        repo = Path(repo_root).expanduser().resolve()
        relative_posix = candidate.relative_to(repo).as_posix()
        if required_prefix and not relative_posix.startswith(required_prefix):
            return f"{message}: artifact at index {index} is outside the required directory"
        if allowed_suffixes and not relative_posix.lower().endswith(allowed_suffixes):
            return f"{message}: artifact at index {index} has an unsupported file type"
        if require_non_empty_content:
            text = _read_safe_repo_text(repo_root, item)
            if text is None or not text.strip():
                return f"{message}: artifact at index {index} is empty or unreadable"
    return None


def _no_unresolved_findings_error(output: dict, template: dict, message: str) -> str | None:
    when = template.get("when")
    if when is not None:
        if not isinstance(when, dict):
            return message
        when_key = str(when.get("output_key") or "")
        if not condition_matches(output.get(when_key), str(when.get("operator") or ""), when.get("value")):
            return None
    findings = output.get(str(template.get("output_key") or ""))
    if not isinstance(findings, list):
        return message
    unresolved_terms = tuple(str(item).lower() for item in template.get("unresolved_terms") or [])
    resolved_terms = tuple(str(item).lower() for item in template.get("resolved_terms") or [])
    for finding in findings:
        if not isinstance(finding, str) or not finding.strip():
            return message
        lowered = finding.lower()
        unresolved = any(term and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered) for term in unresolved_terms)
        resolved = any(term and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered) for term in resolved_terms)
        if unresolved and not resolved:
            return f"{message}: unresolved findings present"
    return None


_MAX_SAFE_REPO_TEXT_BYTES = 512 * 1024


def _safe_repo_path(repo_root: str, raw_path: str) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    try:
        repo = Path(repo_root).expanduser().resolve()
        normalized = raw_path
        if normalized != normalized.strip() or "\\" in normalized or any(ord(char) < 32 for char in normalized) or normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
            return None
        parts = normalized.split("/")
        if any(part in ("", ".", "..") for part in parts):
            return None
        candidate = repo.joinpath(*parts)
        resolved = candidate.resolve(strict=False)
        relative = resolved.relative_to(repo)
        current = repo
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return None
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def _safe_repo_file(repo_root: str, raw_path: str) -> Path | None:
    candidate = _safe_repo_path(repo_root, raw_path)
    if candidate is None or candidate.is_symlink() or not candidate.is_file():
        return None
    return candidate


def _read_safe_repo_text(repo_root: str, raw_path: str) -> str | None:
    candidate = _safe_repo_file(repo_root, raw_path)
    if candidate is None:
        return None
    file_descriptor = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        file_descriptor = os.open(str(candidate), flags)
        with os.fdopen(file_descriptor, "rb") as handle:
            file_descriptor = None
            data = handle.read(_MAX_SAFE_REPO_TEXT_BYTES + 1)
            if len(data) > _MAX_SAFE_REPO_TEXT_BYTES:
                return None
            return data.decode("utf-8")
    except (OSError, UnicodeError):
        return None
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass


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
