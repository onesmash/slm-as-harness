from __future__ import annotations

import os
import re
import pathlib
import workflows.co_storm_autonomous_research.citation_locators

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
 'expert_results_complete': 'boolean',
 'evidence_registry': 'string[]'},
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
        optional_schema={},
        verifier_rules=[{'output_key': 'last_turn_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Each autonomous round must return a non-empty turn summary.'},
 {'output_key': 'round_decision',
  'operator': 'one_of',
  'value': ['continue', 'reorganize', 'report'],
  'message': 'round_decision must be continue, reorganize, or report.'},
 {'output_key': 'report_scope_status',
  'operator': 'one_of',
  'value': ['in_progress', 'complete', 'partial'],
  'message': 'report_scope_status must be in_progress, complete, or partial.'}],
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
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_synthesize_report(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
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
# spec_fingerprint: 4e7e87b942ae363547aa5a60209898b61793ad1c101c35ab1db4fc6314c3faf5
# implementation_version: 5
def _custom_verifier_requirement_launch_expert_subagents_expert_results_match_roster(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Require roster-matching expert results and an append-only merged evidence_registry."""
    persisted_state = state if isinstance(state, dict) else {}
    errors: list[str] = []
    citation_pattern = re.compile(r"\[([0-9]+)\]")
    numbered_entry_pattern = re.compile(r"^[ \t]*\[([0-9]+)\][ \t]*(.+?)[ \t]*$")
    max_registry_entries = 128
    max_unused_per_expert = 3
    max_safe_artifact_bytes = 512 * 1024
    max_citation_id_digits = 6

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

    def locator_key(detail: str) -> str:
        text = detail.strip()
        if " — " in text:
            text = text.split(" — ", 1)[0].strip()
        return text.casefold()

    def citation_ids_for_text(text: str, label: str) -> set[int]:
        citation_ids, parse_error = workflows.co_storm_autonomous_research.citation_locators.extract_citation_ids(
            text
        )
        if parse_error is not None or citation_ids is None:
            errors.append(f"{label} contains invalid citation markers")
            return set()
        return citation_ids

    persisted_registry = persisted_state.get("evidence_registry")
    persisted_prefix: list[str] = []
    persisted_ids: set[int] = set()
    persisted_locators: set[str] = set()
    if not isinstance(persisted_registry, list) or not persisted_registry:
        errors.append("persisted evidence_registry must contain grounded entries")
    else:
        for index, entry in enumerate(persisted_registry):
            if not isinstance(entry, str):
                errors.append(f"persisted evidence_registry[{index}] must be a string")
                continue
            persisted_prefix.append(entry)
            match = numbered_entry_pattern.match(entry)
            if match is None:
                errors.append(f"persisted evidence_registry[{index}] must contain a citation identifier and claim")
                continue
            raw_id = match.group(1)
            if len(raw_id) > max_citation_id_digits:
                errors.append(f"persisted evidence_registry[{index}] has an oversized citation identifier")
                continue
            evidence_id = int(raw_id)
            detail = match.group(2).strip()
            if not detail:
                errors.append(f"persisted evidence_registry[{index}] must contain a non-empty claim")
                continue
            if evidence_id in persisted_ids:
                errors.append(f"persisted evidence_registry contains duplicate citation identifier {evidence_id}")
            persisted_ids.add(evidence_id)
            persisted_locators.add(locator_key(detail))

    results = output.get("expert_results")
    if not isinstance(results, list):
        errors.append("expert_results must be a list")
    elif expected_ids and len(results) != len(expected_ids):
        errors.append(f"expert_results must contain exactly {len(expected_ids)} results, actual {len(results)}")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    ordered_new_evidence: list[list[str]] = []
    artifact_texts: dict[int, str] = {}
    if isinstance(results, list):
        for index, result in enumerate(results):
            if not isinstance(result, dict):
                errors.append(f"expert_results[{index}] must be an object")
                ordered_new_evidence.append([])
                continue
            if set(result) != {"expert_id", "summary", "artifact_path", "new_evidence"}:
                errors.append(
                    f"expert_results[{index}] must contain exactly expert_id, summary, artifact_path, and new_evidence"
                )
                ordered_new_evidence.append([])
                continue
            expert_id = result.get("expert_id")
            summary = result.get("summary")
            artifact_path = result.get("artifact_path")
            new_evidence = result.get("new_evidence")
            if not isinstance(expert_id, str) or not expert_id.strip():
                errors.append(f"expert_results[{index}].expert_id must be a non-empty string")
            else:
                expert_id = expert_id.strip()
                if expert_id in seen_ids:
                    errors.append(f"expert_results contains duplicate expert_id {expert_id!r}")
                seen_ids.add(expert_id)
                if index < len(expected_ids) and expert_id != expected_ids[index]:
                    errors.append(
                        f"expert_results[{index}].expert_id must be {expected_ids[index]!r}, actual {expert_id!r}"
                    )
                elif expert_id not in expected_ids:
                    errors.append(f"expert_results contains unknown expert_id {expert_id!r}")
            if not isinstance(summary, str) or not summary.strip():
                errors.append(f"expert_results[{index}].summary must be a non-empty string")
            cleaned_new_evidence: list[str] = []
            if not isinstance(new_evidence, list):
                errors.append(f"expert_results[{index}].new_evidence must be a list")
            else:
                for evidence_index, item in enumerate(new_evidence):
                    if not isinstance(item, str) or not item.strip():
                        errors.append(f"expert_results[{index}].new_evidence[{evidence_index}] must be a non-empty string")
                        continue
                    stripped = item.strip()
                    if citation_pattern.search(stripped):
                        errors.append(
                            f"expert_results[{index}].new_evidence[{evidence_index}] must not contain citation markers"
                        )
                        continue
                    if stripped.count(" — ") != 1:
                        errors.append(
                            f"expert_results[{index}].new_evidence[{evidence_index}] must use the form locator — claim"
                        )
                        continue
                    locator, claim = stripped.split(" — ", 1)
                    if not locator.strip() or not claim.strip():
                        errors.append(
                            f"expert_results[{index}].new_evidence[{evidence_index}] must include a non-empty locator and claim"
                        )
                        continue
                    cleaned_new_evidence.append(stripped)
            ordered_new_evidence.append(cleaned_new_evidence)
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
                    data = handle.read(max_safe_artifact_bytes + 1)
                if len(data) > max_safe_artifact_bytes:
                    raise ValueError("artifact is too large")
                artifact_texts[index] = data.decode("utf-8")
            except (OSError, UnicodeError, RuntimeError, ValueError):
                errors.append(f"expert_results[{index}].artifact_path must identify a safe, bounded UTF-8 repository file")

    expected_registry = list(persisted_prefix)
    expected_ids_set = set(persisted_ids)
    seen_locators = set(persisted_locators)
    next_id = (max(persisted_ids) + 1) if persisted_ids else 1
    locator_to_id: dict[str, int] = {}
    for entry in persisted_prefix:
        match = numbered_entry_pattern.match(entry)
        if match is not None:
            raw_id = match.group(1)
            if len(raw_id) <= max_citation_id_digits:
                locator_to_id[locator_key(match.group(2))] = int(raw_id)
    for items in ordered_new_evidence:
        for item in items:
            key = locator_key(item)
            if key in seen_locators:
                continue
            seen_locators.add(key)
            expected_registry.append(f"[{next_id}] {item}")
            expected_ids_set.add(next_id)
            locator_to_id[key] = next_id
            next_id += 1

    returned_registry = output.get("evidence_registry")
    if not isinstance(returned_registry, list):
        errors.append("evidence_registry must be a list")
    else:
        if len(returned_registry) > max_registry_entries or len(expected_registry) > max_registry_entries:
            errors.append(f"evidence_registry must contain at most {max_registry_entries} entries")
        if persisted_prefix and (
            len(returned_registry) < len(persisted_prefix)
            or returned_registry[: len(persisted_prefix)] != persisted_prefix
        ):
            errors.append("evidence_registry must preserve the persisted prefix")
        if returned_registry != expected_registry:
            errors.append("evidence_registry must equal the persisted prefix plus newly merged contiguous entries")

    merged_ids = set()
    if isinstance(returned_registry, list) and returned_registry == expected_registry:
        for entry in returned_registry:
            match = numbered_entry_pattern.match(entry) if isinstance(entry, str) else None
            if match is not None:
                raw_id = match.group(1)
                if len(raw_id) <= max_citation_id_digits:
                    merged_ids.add(int(raw_id))
    elif persisted_ids:
        merged_ids = set(expected_ids_set)

    if isinstance(results, list) and merged_ids:
        for index, result in enumerate(results):
            if not isinstance(result, dict):
                continue
            summary = result.get("summary")
            summary_ids: set[int] = set()
            if isinstance(summary, str) and summary.strip():
                summary_ids = citation_ids_for_text(
                    summary,
                    f"expert_results[{index}].summary",
                )
            artifact_text = artifact_texts.get(index)
            artifact_ids: set[int] = set()
            if isinstance(artifact_text, str):
                artifact_ids = citation_ids_for_text(
                    artifact_text,
                    f"expert_results[{index}].artifact_path",
                )
            if summary_ids - merged_ids:
                errors.append(f"expert_results[{index}].summary must cite only merged evidence entries")
            if artifact_ids - merged_ids:
                errors.append(f"expert_results[{index}].artifact_path must contain only merged evidence citations")
            cited_ids = summary_ids | artifact_ids
            if not cited_ids.intersection(merged_ids):
                errors.append(f"expert_results[{index}] must cite at least one merged evidence entry")
            unused_count = 0
            new_evidence = result.get("new_evidence")
            if isinstance(new_evidence, list):
                for item in new_evidence:
                    if not isinstance(item, str) or not item.strip():
                        continue
                    assigned_id = locator_to_id.get(locator_key(item.strip()))
                    if assigned_id is None or assigned_id not in cited_ids:
                        unused_count += 1
                if unused_count > max_unused_per_expert:
                    errors.append(
                        f"expert_results[{index}].new_evidence may include at most {max_unused_per_expert} unused retrieved items"
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
    message = _custom_verifier_requirement_autonomous_roundtable_merged_evidence_registry_is_preserved(
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
# spec_fingerprint: 6fee3be45117ff26f7ce42d0b28037a3d26fb9b9407e34e52d8751f31a3c9ac6
# implementation_version: 6
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

Requirement: The autonomous roundtable must select exactly one routing decision, preserve the prior transcript, advance exactly one round, require a completed expert-result package, and provide a deterministic topic-level semantic coverage assessment.
Signals: round_decision, continue_roundtable, should_reorganize, ready_for_report, coverage_assessment, coverage_decision_rationale, next_round_validation_plan, report_scope_status, expert_results, expert_results_complete
Implementation surfaces: verifiers.py, policy.py, workflow-specific regression tests
Hint pseudocode:
- Count the three decision flags and require exactly one true value.
- Map continue to continue_roundtable, reorganize to should_reorganize, and report to ready_for_report.
- Require output.round_index to equal persisted state.round_index + 1 and require the returned transcript to preserve the persisted transcript as an exact prefix plus one new turn.
- Require persisted expert_results_complete to be true and persisted expert_results to be non-empty before the Moderator can accept a round.
- Require the Moderator to carry forward the persisted structured expert roster exactly.
- Reject round_index values below one, reject values above constraints.max_rounds, and reject continue or reorganize once max_rounds has been reached.
- Require coverage_assessment records to have exactly topic_id, status, evidence_refs, open_gaps, and next_validation_metrics; topic ids must be non-empty and unique, statuses must be covered, bounded_gap, or missing, and evidence refs must resolve to evidence_registry ids.
- Require all persisted coverage_map topics to appear verbatim as assessed topic ids on the first round, and preserve all topic ids from persisted coverage_assessment on later rounds.
- Treat coverage_threshold only as a minimum number of assessed topics. Reject coverage_sufficient=true unless no topic is missing, covered topics have evidence and no gaps or metrics, and bounded gaps have evidence, explicit gaps, and metrics; allow the Moderator to keep coverage_sufficient=false for material bounded gaps.
- When coverage_sufficient is false, require next_round_validation_plan to equal the complete set of `topic_id — metric` strings for every missing topic and every bounded_gap topic the Moderator keeps unresolved.
- Require continue to carry a missing or materially unresolved bounded_gap topic; require complete report to have sufficient coverage and no pending plan.
- At max_rounds, allow insufficient coverage only as a partial report with a non-empty next_round_validation_plan; never mark forced stopping as complete.
Test intent:
- Accept a continue decision with only continue_roundtable true, a strictly incremented round, and one appended transcript turn.
- Reject ambiguous decisions with two true flags.
- Reject a report decision before semantic coverage is sufficient unless max_rounds has been reached and the report is explicitly partial.
- Reject coverage_sufficient when threshold-sized topic counts still include a missing topic.
- Accept a Moderator continuation when a structurally valid bounded gap is judged material and its metrics are carried into the plan.
- Reject a covered topic that still contains gaps or validation metrics.
- Reject a first-round assessment that replaces a warm-start coverage topic.
- Reject a validation plan that is unrelated to or omits an unresolved topic metric.
- Reject missing, malformed, or unresolvable evidence references in the semantic assessment.
- Reject a skipped round or a rewritten transcript prefix.
- Reject a Moderator turn that has no completed expert-result package."""
    import json
    import re

    _ = repo_root
    persisted_state = state if isinstance(state, dict) else {}
    errors: list[str] = []

    decision_to_flag = {
        "continue": "continue_roundtable",
        "reorganize": "should_reorganize",
        "report": "ready_for_report",
    }
    flag_values = {name: output.get(name) for name in decision_to_flag.values()}
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

    rationale = output.get("coverage_decision_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("coverage_decision_rationale must be meaningful text")
    scope_status = output.get("report_scope_status")
    if scope_status not in {"in_progress", "complete", "partial"}:
        errors.append("report_scope_status must be in_progress, complete, or partial")
    validation_plan = output.get("next_round_validation_plan")
    plan_is_valid = isinstance(validation_plan, list) and all(
        isinstance(item, str) and item.strip() for item in validation_plan
    )
    if not plan_is_valid:
        errors.append("next_round_validation_plan must be a list of meaningful strings")
        validation_plan = []
    elif len(validation_plan) > 128 or len(
        json.dumps(validation_plan, ensure_ascii=False).encode("utf-8")
    ) > 64 * 1024:
        errors.append("next_round_validation_plan exceeds durable state limits")

    registry = output.get("evidence_registry")
    available_evidence_ids: set[str] = set()
    if isinstance(registry, list):
        for entry in registry:
            if isinstance(entry, str):
                match = re.match(r"^\[(\d+)\]", entry.strip())
                if match:
                    available_evidence_ids.add(f"[{match.group(1)}]")

    assessment = output.get("coverage_assessment")
    expected_keys = {
        "topic_id",
        "status",
        "evidence_refs",
        "open_gaps",
        "next_validation_metrics",
    }
    topic_ids: set[str] = set()
    missing_topic_ids: set[str] = set()
    bounded_gap_topic_ids: set[str] = set()
    expected_plan_items: set[str] = set()
    assessment_semantics_valid = True
    if not isinstance(assessment, list) or not assessment:
        errors.append("coverage_assessment must contain at least one assessed topic")
        assessment_semantics_valid = False
        assessment = []
    elif len(assessment) > 128 or len(
        json.dumps(assessment, ensure_ascii=False).encode("utf-8")
    ) > 64 * 1024:
        errors.append("coverage_assessment exceeds durable state limits")
        assessment_semantics_valid = False
    for index, item in enumerate(assessment):
        label = f"coverage_assessment[{index}]"
        if not isinstance(item, dict) or set(item) != expected_keys:
            errors.append(f"{label} must contain exactly {sorted(expected_keys)}")
            assessment_semantics_valid = False
            continue
        topic_id = item.get("topic_id")
        if not isinstance(topic_id, str) or not topic_id.strip():
            errors.append(f"{label}.topic_id must be meaningful text")
            assessment_semantics_valid = False
            continue
        topic_id = topic_id.strip()
        if topic_id in topic_ids:
            errors.append(f"coverage_assessment topic_id {topic_id!r} must be unique")
            assessment_semantics_valid = False
        topic_ids.add(topic_id)

        status = item.get("status")
        if status not in {"covered", "bounded_gap", "missing"}:
            errors.append(f"{label}.status must be covered, bounded_gap, or missing")
            assessment_semantics_valid = False
            continue
        evidence_refs = item.get("evidence_refs")
        open_gaps = item.get("open_gaps")
        metrics = item.get("next_validation_metrics")
        for field_name, value in (
            ("evidence_refs", evidence_refs),
            ("open_gaps", open_gaps),
            ("next_validation_metrics", metrics),
        ):
            if not isinstance(value, list) or any(
                not isinstance(entry, str) or not entry.strip() for entry in value
            ):
                errors.append(f"{label}.{field_name} must be a list of meaningful strings")
                assessment_semantics_valid = False
        evidence_refs = evidence_refs if isinstance(evidence_refs, list) else []
        open_gaps = open_gaps if isinstance(open_gaps, list) else []
        metrics = metrics if isinstance(metrics, list) else []
        for evidence_ref in evidence_refs:
            if not isinstance(evidence_ref, str) or not re.fullmatch(r"\[\d+\]", evidence_ref.strip()):
                errors.append(f"{label}.evidence_refs must contain citation ids such as [1]")
                assessment_semantics_valid = False
            elif evidence_ref.strip() not in available_evidence_ids:
                errors.append(f"{label} references unknown evidence id {evidence_ref!r}")
                assessment_semantics_valid = False
        if status == "covered":
            if not evidence_refs:
                errors.append(f"{label} marked covered must cite at least one evidence id")
                assessment_semantics_valid = False
            if open_gaps or metrics:
                errors.append(f"{label} marked covered must not retain open gaps or validation metrics")
                assessment_semantics_valid = False
        elif status == "bounded_gap":
            bounded_gap_topic_ids.add(topic_id)
            if not evidence_refs or not open_gaps or not metrics:
                errors.append(f"{label} marked bounded_gap requires evidence, open gaps, and validation metrics")
                assessment_semantics_valid = False
            expected_plan_items.update(
                f"{topic_id} — {metric.strip()}"
                for metric in metrics
                if isinstance(metric, str) and metric.strip()
            )
        elif status == "missing":
            missing_topic_ids.add(topic_id)
            if not open_gaps or not metrics:
                errors.append(f"{label} marked missing requires open gaps and validation metrics")
                assessment_semantics_valid = False
            expected_plan_items.update(
                f"{topic_id} — {metric.strip()}"
                for metric in metrics
                if isinstance(metric, str) and metric.strip()
            )

    persisted_coverage_map = persisted_state.get("coverage_map")
    required_topic_ids = {
        item.strip()
        for item in persisted_coverage_map
        if isinstance(item, str) and item.strip()
    } if isinstance(persisted_coverage_map, list) else set()
    previous_assessment = persisted_state.get("coverage_assessment")
    if isinstance(previous_assessment, list) and previous_assessment:
        required_topic_ids.update(
            item.get("topic_id").strip()
            for item in previous_assessment
            if isinstance(item, dict)
            and isinstance(item.get("topic_id"), str)
            and item.get("topic_id").strip()
        )
    dropped_topic_ids = sorted(required_topic_ids - topic_ids)
    if dropped_topic_ids:
        errors.append(f"coverage_assessment dropped required topic ids: {dropped_topic_ids}")
        assessment_semantics_valid = False

    output_coverage_map = output.get("coverage_map")
    if isinstance(output_coverage_map, list):
        if len(output_coverage_map) > 128 or len(
            json.dumps(output_coverage_map, ensure_ascii=False).encode("utf-8")
        ) > 64 * 1024:
            errors.append("coverage_map exceeds durable state limits")
            assessment_semantics_valid = False
        unassessed_map_topics = sorted({
            item.strip()
            for item in output_coverage_map
            if isinstance(item, str) and item.strip()
        } - topic_ids)
        if unassessed_map_topics:
            errors.append(f"coverage_map contains unassessed topic ids: {unassessed_map_topics}")
            assessment_semantics_valid = False

    coverage_threshold = constraints.get("coverage_threshold", 2)
    threshold_met = False
    if not isinstance(coverage_threshold, int) or isinstance(coverage_threshold, bool) or coverage_threshold <= 0:
        errors.append("constraints.coverage_threshold must be a positive integer when supplied")
    else:
        threshold_met = len(topic_ids) >= coverage_threshold
        if not threshold_met:
            errors.append(f"coverage_assessment must contain at least {coverage_threshold} distinct topics")

    guardrails_allow_completion = assessment_semantics_valid and threshold_met and not missing_topic_ids
    coverage_sufficient = output.get("coverage_sufficient")
    if not isinstance(coverage_sufficient, bool):
        errors.append("coverage_sufficient must be a boolean")
    elif coverage_sufficient and not guardrails_allow_completion:
        errors.append("coverage_sufficient=true violates deterministic semantic guardrails")

    unresolved_topic_ids = missing_topic_ids | (bounded_gap_topic_ids if coverage_sufficient is False else set())
    required_plan_items = expected_plan_items if coverage_sufficient is False else set()
    actual_plan_items = {
        item.strip() for item in validation_plan if isinstance(item, str) and item.strip()
    }
    if coverage_sufficient is False and (
        actual_plan_items != required_plan_items or len(validation_plan) != len(actual_plan_items)
    ):
        errors.append(
            "next_round_validation_plan must exactly match every unresolved `topic_id — metric` item"
        )
    if coverage_sufficient is True and validation_plan:
        errors.append("coverage_sufficient=true requires an empty next_round_validation_plan")

    if decision == "continue":
        if coverage_sufficient is not False:
            errors.append("continue requires coverage_sufficient=false")
        if scope_status != "in_progress":
            errors.append("continue requires report_scope_status=in_progress")
        if not unresolved_topic_ids:
            errors.append("continue requires a missing or materially unresolved bounded-gap topic")
    elif decision == "reorganize":
        if coverage_sufficient is not False:
            errors.append("reorganize requires coverage_sufficient=false")
        if scope_status != "in_progress":
            errors.append("reorganize requires report_scope_status=in_progress")
    elif decision == "report":
        if coverage_sufficient is True:
            if scope_status != "complete":
                errors.append("Moderator-approved report requires report_scope_status=complete")
        else:
            if round_index != max_rounds:
                errors.append("incomplete coverage may report only when max_rounds is reached")
            if scope_status != "partial":
                errors.append("forced report with incomplete coverage requires report_scope_status=partial")
            if not validation_plan:
                errors.append("partial report requires a non-empty next_round_validation_plan")

    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: autonomous_roundtable
# custom_verifier_requirement_id: merged_evidence_registry_is_preserved
# template_version: 1
# spec_fingerprint: bdddaa160dc52d3b77ec1a3cdbf3791a9361612f2692a4088d0d0b666bf5dced
# implementation_version: 1
def _custom_verifier_requirement_autonomous_roundtable_merged_evidence_registry_is_preserved(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: The Moderator must carry forward the merged evidence_registry exactly; new numbered evidence is produced only by launch_expert_subagents.
Signals: evidence_registry
Implementation surfaces: verifiers.py, workflow-specific regression tests
Hint pseudocode:
- Require persisted evidence_registry to be a non-empty list of strings.
- Require output.evidence_registry to equal the persisted list exactly (same strings and order).
- Reject dropped, rewritten, reordered, or newly numbered registry rows.
Test intent:
- Accept a Moderator turn that returns the persisted merged registry unchanged.
- Reject a Moderator turn that drops a merged citation or rewrites a persisted row."""
    _ = repo_root
    persisted_state = state if isinstance(state, dict) else {}
    persisted_registry = persisted_state.get("evidence_registry")
    if not isinstance(persisted_registry, list) or not persisted_registry:
        return "persisted evidence_registry must contain merged entries"
    if any(not isinstance(entry, str) for entry in persisted_registry):
        return "persisted evidence_registry entries must be strings"
    returned_registry = output.get("evidence_registry")
    if not isinstance(returned_registry, list):
        return "evidence_registry must be a list"
    if returned_registry != persisted_registry:
        return "evidence_registry must equal the persisted merged registry"
    return None

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
# spec_fingerprint: a33b03befbc54107863f33320f4a91a651f60e982958f41977e8564cf5b8a839
# implementation_version: 3
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

Requirement: Knowledge-space reorganization must advance the counter exactly once, preserve the evidence registry exactly, and respect the autonomous reorganization budget.
Signals: reorganization_count, reorganized
Implementation surfaces: verifiers.py, workflow-specific regression tests
Hint pseudocode:
- Require reorganization_count to be an integer greater than zero and exactly one greater than persisted state.reorganization_count.
- Read constraints.max_reorganizations from persisted state and reject counts above that value or a reorganization after the budget is exhausted.
- Require output.evidence_registry to equal persisted state.evidence_registry exactly, including strings and order; reject additions, rewrites, reordering, and deletion.
Test intent:
- Accept the first reorganization when the configured budget is two.
- Reject a reorganization count above the configured budget.
- Reject a reorganization that skips a counter value.
- Reject a reorganization that adds, rewrites, reorders, or deletes any evidence registry row."""
    _ = repo_root
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
        if (
            not isinstance(max_reorganizations, int)
            or isinstance(max_reorganizations, bool)
            or max_reorganizations < 1
        ):
            return "constraints.max_reorganizations must be a positive integer when supplied"
        if count > max_reorganizations:
            return "reorganization_count exceeds constraints.max_reorganizations"

    persisted_registry = persisted_state.get("evidence_registry")
    if not isinstance(persisted_registry, list) or not persisted_registry:
        return "persisted evidence_registry must contain grounded entries"
    if any(not isinstance(entry, str) or not entry.strip() for entry in persisted_registry):
        return "persisted evidence_registry entries must be meaningful strings"
    if output.get("evidence_registry") != persisted_registry:
        return "reorganization must preserve evidence_registry exactly"
    return None
    # Implementation notes retained from the generated requirement scaffold.
    # Intended implementation surfaces: verifiers.py, workflow-specific regression tests.
    # Verifier scaffolding is provided as context only; implement the
    # primary logic in the declared non-verifier surfaces as well.
    # Hint pseudocode:
    # - Require reorganization_count to be an integer greater than zero and exactly one greater than persisted state.reorganization_count.
    # - Read constraints.max_reorganizations from persisted state and reject counts above that value or a reorganization after the budget is exhausted.
    # - Require output.evidence_registry to equal persisted state.evidence_registry exactly, including strings and order; reject additions, rewrites, reordering, and deletion.
    # Test intent:
    # - Accept the first reorganization when the configured budget is two.
    # - Reject a reorganization count above the configured budget.
    # - Reject a reorganization that skips a counter value.
    # - Reject a reorganization that adds, rewrites, reorders, or deletes any evidence registry row.
    # This scaffold is generated during initial workflow authoring so the
    # review pass can validate or refine concrete verifier logic instead
    # of creating it from scratch.
    return None

def _run_custom_verifier_requirements_synthesize_report(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_synthesize_report_report_uses_compact_evidence_index(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: synthesize_report
# custom_verifier_requirement_id: report_uses_compact_evidence_index
# template_version: 1
# spec_fingerprint: dfdfa048a8504177622b3d7a3e216c552d19df8c6782014dc34edef89a029ef5
# implementation_version: 1
def _custom_verifier_requirement_synthesize_report_report_uses_compact_evidence_index(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: The rendered report body may use compact number-only [n] citations for readability, but it must end with exactly one Evidence index containing one exact source-locator-only row for every citation id used in the body.
Signals: report_path, report_sections, context, evidence_registry
Implementation surfaces: verifiers.py, workflow-specific regression tests
Hint pseudocode:
- Read the repository-relative report_path from structured_output safely under repo_root.
- When context.output_dir is set, require the report artifact to remain under that canonical repository-relative output directory.
- Verify that report_sections names at least two substantive rendered Markdown sections and matches the report artifact rather than relying only on the LLM-declared count.
- Parse evidence_registry rows as [n] locator — optional claim; the locator is the text after [n] and before an em-dash separator, else the remainder of the row.
- Strip HTML comments and raw HTML blocks, then identify the report body as the content before exactly one `## Evidence index` heading, allowing an optional numeric section prefix or the equivalent Chinese `## 证据索引` heading.
- Extract bounded ASCII numeric [n] markers from the rendered report body, ignoring inline and fenced or indented Markdown code; reject oversized citation identifiers and unclosed comments or code spans.
- Parse Evidence index rows in the exact form `- [n] locator`; allow one surrounding pair of Markdown backticks around the locator, but reject any ` — claim` suffix.
- Require every body citation id to have exactly one matching index row whose locator equals the evidence_registry locator, reject duplicate, unknown, missing, empty, or unused index rows, and reject any registry locator repeated in the rendered report body.
- Reject when the report has numeric body citations but no valid Evidence index, or when substantive content appears after the Evidence index.
Test intent:
- Accept a report whose body uses source [1] and source [2] and whose final Evidence index maps each id to the exact registry locator.
- Reject a report that only writes [1] and [2] without an Evidence index.
- Reject a report with duplicate, unknown, missing, or mismatched Evidence index rows.
- Reject a report with substantive content after the Evidence index.
- Reject a report that repeats a registry locator in the body, or hides a citation/index inside Markdown code."""
    persisted_state = state if isinstance(state, dict) else {}
    context = persisted_state.get("context")
    output_dir = context.get("output_dir") if isinstance(context, dict) else None
    if not workflows.co_storm_autonomous_research.citation_locators.report_path_is_within_output_dir(
        repo_root,
        output.get("report_path"),
        output_dir,
    ):
        return "report_path must remain under the configured context.output_dir"
    report_text, error = workflows.co_storm_autonomous_research.citation_locators.load_utf8_report(
        repo_root,
        output.get("report_path"),
    )
    if error is not None:
        return error
    if report_text is None:
        return "report file could not be loaded"
    section_error = (
        workflows.co_storm_autonomous_research.citation_locators.missing_substantive_report_sections(
            report_text,
            output.get("report_sections"),
        )
    )
    if section_error is not None:
        return section_error
    return workflows.co_storm_autonomous_research.citation_locators.missing_evidence_index(
        report_text,
        persisted_state.get("evidence_registry"),
    )

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
    message = _custom_verifier_requirement_verify_report_report_uses_compact_evidence_index(
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
# spec_fingerprint: b51886277a0c58d744ca85da968abdbe4cebeec336060c8d8c9d209777189ebe
# implementation_version: 4
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

Requirement: Every numeric inline citation must resolve to grounded evidence, and the report must deterministically preserve the Moderator's complete-or-partial scope decision and all unresolved validation work before a pass can finalize.
Signals: report_path, verified_report_path, report_sections, context, evidence_registry, report_ready, quality_verdict, quality_findings, coverage_map, coverage_assessment, coverage_sufficient, next_round_validation_plan, report_scope_status
Implementation surfaces: verifiers.py, workflow-specific regression tests
Hint pseudocode:
- Read the repository-relative report path safely under repo_root.
- When context.output_dir is set, require report_path and verified_report_path to remain under that canonical repository-relative output directory.
- Verify declared report_sections against at least two substantive rendered Markdown sections when the state carries report_sections.
- Extract bounded ASCII numeric markers such as [1] from rendered Markdown and parse bounded numeric identifiers from evidence_registry entries; reject oversized identifiers instead of converting them to integers.
- Reject unknown markers, missing or empty evidence entries, or a pass verdict with no citation markers.
- Require verified_report_path to resolve to the same repository-relative regular file as report_path.
- Require `Report scope: complete` only when state.report_scope_status is complete, coverage_sufficient is true, and next_round_validation_plan is empty.
- Require `Report scope: partial` when state.report_scope_status is partial and require the report to contain every unresolved topic_id, open_gap, next_validation_metric, and top-level next_round_validation_plan item verbatim.
- Ignore citations inside Markdown code and reject unresolved critical or blocker findings when quality_verdict is pass; make a repair verdict fail this verifier so policy enters repair_report.
Test intent:
- Accept a report whose [1] and [2] markers exist in the evidence registry.
- Reject a report containing an unknown [99] marker.
- Reject a pass verdict for an uncited report.
- Reject a pass verdict with an unresolved critical finding.
- Accept a partial report that explicitly discloses every unresolved topic, gap, metric, and plan item.
- Reject a partial report that omits its marker or any unresolved validation item.
- Reject a complete report when coverage_sufficient is false or validation work remains.
- Reject a repair verdict as a verifier failure so the repair route is taken."""
    persisted_state = state if isinstance(state, dict) else {}
    if output.get("quality_verdict") == "repair":
        return "quality_verdict=repair requires report repair before verification"

    report_path = persisted_state.get("report_path")
    verified_report_path = output.get("verified_report_path")
    context = persisted_state.get("context")
    output_dir = context.get("output_dir") if isinstance(context, dict) else None
    if not all(
        workflows.co_storm_autonomous_research.citation_locators.report_path_is_within_output_dir(
            repo_root,
            path,
            output_dir,
        )
        for path in (report_path, verified_report_path)
    ):
        return "report_path and verified_report_path must remain under the configured context.output_dir"
    report_file = workflows.co_storm_autonomous_research.citation_locators.resolve_safe_repo_file(
        repo_root,
        report_path,
    )
    verified_report_file = workflows.co_storm_autonomous_research.citation_locators.resolve_safe_repo_file(
        repo_root,
        verified_report_path,
    )
    if report_file is None or verified_report_file is None:
        return "report_path and verified_report_path must identify readable repository files"
    if report_file != verified_report_file:
        return "verified_report_path must resolve to the synthesized report artifact"

    report_text, error = workflows.co_storm_autonomous_research.citation_locators.load_utf8_report(
        repo_root,
        report_path,
    )
    if error is not None:
        return error
    if report_text is None:
        return "report file could not be loaded"
    if persisted_state.get("report_sections"):
        section_error = (
            workflows.co_storm_autonomous_research.citation_locators.missing_substantive_report_sections(
                report_text,
                persisted_state.get("report_sections"),
            )
        )
        if section_error is not None:
            return section_error

    registry = workflows.co_storm_autonomous_research.citation_locators.parse_registry_locators(
        persisted_state.get("evidence_registry")
    )
    if isinstance(registry, str):
        return registry
    citation_ids, error = workflows.co_storm_autonomous_research.citation_locators.extract_citation_ids(
        report_text
    )
    if error is not None:
        return error
    if citation_ids is None:
        return "report citation identifiers could not be parsed"
    if not citation_ids:
        return "pass-quality report must contain at least one rendered numeric citation"
    unknown_ids = sorted(citation_ids - set(registry))
    if unknown_ids:
        return f"report contains citation identifiers absent from evidence_registry: {unknown_ids}"

    rendered, error = workflows.co_storm_autonomous_research.citation_locators.rendered_report_text(
        report_text
    )
    if error is not None:
        return error
    if rendered is None:
        return "report could not be rendered"

    scope_status = persisted_state.get("report_scope_status")
    scope_marker = f"Report scope: {scope_status}"
    if scope_status not in {"complete", "partial"}:
        return "persisted report_scope_status must be complete or partial"
    if scope_marker not in rendered:
        return f"report must contain the exact `{scope_marker}` line"

    raw_assessment = persisted_state.get("coverage_assessment")
    if not isinstance(raw_assessment, list) or not raw_assessment:
        return "coverage_assessment must contain at least one structured topic record"
    assessment = []
    topic_ids: set[str] = set()
    for record in raw_assessment:
        if not isinstance(record, dict):
            return "coverage_assessment records must be objects"
        topic_id = record.get("topic_id")
        status = record.get("status")
        if not isinstance(topic_id, str) or not topic_id.strip():
            return "coverage_assessment topic_id must be a non-empty string"
        if topic_id in topic_ids:
            return "coverage_assessment contains duplicate topic_id values"
        if status not in {"covered", "bounded_gap", "missing"}:
            return f"coverage_assessment has an invalid status for topic {topic_id!r}"
        topic_ids.add(topic_id)
        assessment.append((topic_id, status, record))

    raw_coverage_map = persisted_state.get("coverage_map")
    if raw_coverage_map:
        if not isinstance(raw_coverage_map, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in raw_coverage_map
        ):
            return "coverage_map must contain non-empty topic identifiers"
        if set(raw_coverage_map) != topic_ids:
            return "coverage_assessment topic ids must match coverage_map"

    unresolved = []
    for topic_id, status, record in assessment:
        if status == "covered":
            continue
        open_gaps = record.get("open_gaps")
        next_metrics = record.get("next_validation_metrics")
        if (
            not isinstance(open_gaps, list)
            or not open_gaps
            or any(not isinstance(item, str) or not item.strip() for item in open_gaps)
            or not isinstance(next_metrics, list)
            or not next_metrics
            or any(not isinstance(item, str) or not item.strip() for item in next_metrics)
        ):
            return f"unresolved coverage topic {topic_id!r} must include gaps and validation metrics"
        unresolved.append((topic_id, open_gaps, next_metrics))

    if scope_status == "complete":
        if persisted_state.get("coverage_sufficient") is not True:
            return "complete report requires coverage_sufficient=true"
        if persisted_state.get("next_round_validation_plan"):
            return "complete report cannot retain next-round validation work"
        if unresolved:
            return "complete report cannot contain unresolved coverage topics"
    else:
        if persisted_state.get("coverage_sufficient") is True:
            return "partial report cannot claim coverage_sufficient=true"
        plan = persisted_state.get("next_round_validation_plan")
        if not isinstance(plan, list) or not plan or any(
            not isinstance(item, str) or not item.strip() for item in plan
        ):
            return "partial report requires a non-empty next-round validation plan"
        required_disclosures = [topic_id for topic_id, _, _ in unresolved]
        for _, open_gaps, next_metrics in unresolved:
            required_disclosures.extend(open_gaps)
            required_disclosures.extend(next_metrics)
        required_disclosures.extend(plan)
        for disclosure in required_disclosures:
            if disclosure not in rendered:
                return f"partial report must disclose unresolved item verbatim: {disclosure}"

    unresolved_finding_terms = ("critical", "blocker", "p0")
    resolved_finding_terms = ("resolved", "fixed", "addressed", "cleared")
    for finding in output.get("quality_findings") or []:
        if not isinstance(finding, str) or not finding.strip():
            return "quality_findings must contain meaningful strings"
        lowered = finding.lower()
        mentions_unresolved = any(
            re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered)
            for term in unresolved_finding_terms
        )
        mentions_resolved = any(
            re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered)
            for term in resolved_finding_terms
        )
        if mentions_unresolved and not mentions_resolved:
            return "pass-quality report cannot retain unresolved critical, blocker, or P0 findings"
    return None

# custom_verifier_stage_id: verify_report
# custom_verifier_requirement_id: report_uses_compact_evidence_index
# template_version: 1
# spec_fingerprint: 2632d06f62e49475c9ff35c337ddcdf611ead1b0295dc93220e864c91c3630b0
# implementation_version: 1
def _custom_verifier_requirement_verify_report_report_uses_compact_evidence_index(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: The rendered report body may use compact number-only [n] citations for readability, but it must end with exactly one Evidence index containing one exact source-locator-only row for every citation id used in the body.
Signals: report_path, verified_report_path, report_sections, context, evidence_registry
Implementation surfaces: verifiers.py, workflow-specific regression tests
Hint pseudocode:
- Read the same repository-relative report identified by persisted report_path and verified_report_path.
- When context.output_dir is set, require both report paths to remain under that canonical repository-relative output directory.
- When report_sections is present, verify it against at least two substantive rendered Markdown sections.
- Parse evidence_registry rows as [n] locator — optional claim; the locator is the text after [n] and before an em-dash separator, else the remainder of the row.
- Strip HTML comments, raw HTML blocks, fenced or indented code, and inline code when identifying the rendered report body; reject malformed or unclosed hidden regions.
- Identify the report body as the content before exactly one `## Evidence index` heading, allowing an optional numeric section prefix or the equivalent Chinese `## 证据索引` heading.
- Extract bounded ASCII [n] markers from the rendered body and parse Evidence index rows in the exact form `- [n] locator`; allow one surrounding pair of Markdown backticks around the locator, but reject a claim suffix.
- Require every body citation id to have exactly one matching index row whose locator equals the evidence_registry locator, reject duplicate, unknown, missing, empty, or unused index rows, and reject any registry locator repeated in the rendered body.
- Reject a pass-quality report with missing or invalid Evidence index content, or with substantive content after the Evidence index.
Test intent:
- Accept a report whose body uses source [1] and source [2] and whose final Evidence index maps each id to the exact registry locator.
- Reject a report that only writes [1] and [2] without an Evidence index.
- Reject a report with duplicate, unknown, missing, or mismatched Evidence index rows.
- Reject a report with substantive content after the Evidence index.
- Reject a report whose body repeats a registry locator or whose apparent index is hidden in Markdown code."""
    if output.get("quality_verdict") == "repair":
        return None
    persisted_state = state if isinstance(state, dict) else {}
    report_path = persisted_state.get("report_path")
    verified_report_path = output.get("verified_report_path")
    context = persisted_state.get("context")
    output_dir = context.get("output_dir") if isinstance(context, dict) else None
    if not all(
        workflows.co_storm_autonomous_research.citation_locators.report_path_is_within_output_dir(
            repo_root,
            path,
            output_dir,
        )
        for path in (report_path, verified_report_path)
    ):
        return "report_path and verified_report_path must remain under the configured context.output_dir"
    report_file = workflows.co_storm_autonomous_research.citation_locators.resolve_safe_repo_file(
        repo_root,
        report_path,
    )
    verified_report_file = workflows.co_storm_autonomous_research.citation_locators.resolve_safe_repo_file(
        repo_root,
        verified_report_path,
    )
    if report_file is None or verified_report_file is None:
        return "report_path and verified_report_path must identify readable repository files"
    if report_file != verified_report_file:
        return "verified_report_path must resolve to the synthesized report artifact"
    report_text, error = workflows.co_storm_autonomous_research.citation_locators.load_utf8_report(
        repo_root,
        report_path,
    )
    if error is not None:
        return error
    if report_text is None:
        return "report file could not be loaded"
    if persisted_state.get("report_sections"):
        section_error = (
            workflows.co_storm_autonomous_research.citation_locators.missing_substantive_report_sections(
                report_text,
                persisted_state.get("report_sections"),
            )
        )
        if section_error is not None:
            return section_error
    return workflows.co_storm_autonomous_research.citation_locators.missing_evidence_index(
        report_text,
        persisted_state.get("evidence_registry"),
    )

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
    allowed_keys = set(required_schema) | set(optional_schema)
    unexpected_keys = [
        key for key in output
        if not isinstance(key, str) or key not in allowed_keys
    ]
    if unexpected_keys:
        unexpected = sorted(repr(key) for key in unexpected_keys)
        return _fail(f"unexpected structured_output keys: {unexpected}", run_id, step_id, state)
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
    return f"{key} has unsupported schema type: {schema_type}"


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
        text = _read_safe_repo_text(repo_root, actual)
        return None if text is not None and text.strip() else message
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
_MAX_SAFE_REPO_PATH_BYTES = 2048


def _safe_repo_path(repo_root: str, raw_path: str) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    try:
        repo = Path(repo_root).expanduser().resolve()
        normalized = raw_path
        if normalized != normalized.strip() or len(normalized.encode("utf-8")) > _MAX_SAFE_REPO_PATH_BYTES or "\\" in normalized or any(ord(char) < 32 for char in normalized) or normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
            return None
        parts = normalized.split("/")
        if any(part in ("", ".", "..") for part in parts):
            return None
        current = repo
        for part in parts:
            current = current / part
            if current.is_symlink():
                return None
        candidate = repo.joinpath(*parts)
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(repo)
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
