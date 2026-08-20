from __future__ import annotations

import os
import re

from pathlib import Path

from workflows.common.contracts import VerifierResult, make_verifier_result
from workflows.common.policies import condition_matches

def verify_collect_earnings_packet(
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
        required_schema={'ticker': 'string',
 'reporting_period': 'string',
 'earnings_packet_path': 'string',
 'filings_inventory': 'string[]',
 'actuals_source': 'string',
 'consensus_source': 'string',
 'skip_note': 'boolean',
 'missing_packet_inputs': 'string[]',
 'packet_ready': 'boolean'},
        optional_schema={'transcript_locator': 'string'},
        verifier_rules=[{'output_key': 'ticker',
  'operator': 'truthy',
  'value': None,
  'message': 'ticker must be recorded'},
 {'output_key': 'reporting_period',
  'operator': 'truthy',
  'value': None,
  'message': 'reporting_period must be recorded'},
 {'output_key': 'actuals_source',
  'operator': 'truthy',
  'value': None,
  'message': 'reported actuals must have a source'},
 {'output_key': 'consensus_source',
  'operator': 'truthy',
  'value': None,
  'message': 'consensus must have a source'}],
        verifier_templates=[{'id': 'packet_path_under_out',
  'template': 'repo_path_policy',
  'output_key': 'earnings_packet_path',
  'message': 'earnings packet must be a repository-relative path under out/',
  'required_prefix': 'out/',
  'forbidden_prefixes': [],
  'required_suffix': '.md'},
 {'id': 'filings_inventory_present',
  'template': 'min_count',
  'output_key': 'filings_inventory',
  'message': 'earnings packet must list at least one filing or earnings-release source',
  'min_count': 1},
 {'id': 'ready_packet_requires_transcript',
  'template': 'conditional_required',
  'output_key': 'packet_ready',
  'message': 'a ready earnings packet must include the full call transcript locator',
  'when': {'output_key': 'packet_ready', 'operator': 'is_true', 'value': None},
  'required_key': 'transcript_locator'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_analyze_earnings_call(
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
        required_schema={'headline_read': 'string',
 'beat_miss_summary': 'string',
 'guidance_changes': 'string[]',
 'management_tone': 'string',
 'dodged_questions': 'string[]',
 'thesis_impact': 'string',
 'call_analysis_summary': 'string',
 'unsourced_flags': 'string[]',
 'call_analysis_ready': 'boolean',
 'used_full_transcript': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'headline_read',
  'operator': 'truthy',
  'value': None,
  'message': 'headline_read must not be empty'},
 {'output_key': 'beat_miss_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'beat_miss_summary must not be empty'},
 {'output_key': 'call_analysis_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'call_analysis_summary must not be empty'},
 {'output_key': 'thesis_impact',
  'operator': 'truthy',
  'value': None,
  'message': 'thesis_impact must not be empty'},
 {'output_key': 'used_full_transcript',
  'operator': 'is_true',
  'value': None,
  'message': 'call analysis must use the full transcript, not a snippet summary'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_update_coverage_model(
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
        required_schema={'updated_model_path': 'string',
 'variance_metrics': 'string[]',
 'variance_rows': 'object[]',
 'estimate_change_summary': 'string',
 'price_target_change': 'string',
 'thesis_change_summary': 'string',
 'requires_model_builder_handoff': 'boolean',
 'skip_note': 'boolean',
 'model_update_ready': 'boolean'},
        optional_schema={'handoff_target': 'string', 'handoff_reason': 'string', 'handoff_payload': 'object'},
        verifier_rules=[{'output_key': 'estimate_change_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'estimate_change_summary must not be empty'},
 {'output_key': 'model_update_ready',
  'operator': 'is_true',
  'value': None,
  'message': 'model_update_ready must be true before audit or handoff'}],
        verifier_templates=[{'id': 'updated_model_path_under_out',
  'template': 'repo_path_policy',
  'output_key': 'updated_model_path',
  'message': 'updated coverage model must be a repository-relative .xlsx path under out/',
  'required_prefix': 'out/',
  'forbidden_prefixes': [],
  'required_suffix': '.xlsx'},
 {'id': 'variance_metrics_required',
  'template': 'required_set_members',
  'output_key': 'variance_metrics',
  'message': 'variance table must include Revenue, GM, EBITDA, and EPS',
  'required_members': ['Revenue', 'GM', 'EBITDA', 'EPS'],
  'case_sensitive': False},
 {'id': 'handoff_requires_target',
  'template': 'conditional_required',
  'output_key': 'requires_model_builder_handoff',
  'message': 'a model-builder handoff must include handoff_target',
  'when': {'output_key': 'requires_model_builder_handoff', 'operator': 'is_true', 'value': None},
  'required_key': 'handoff_target'},
 {'id': 'handoff_requires_reason',
  'template': 'conditional_required',
  'output_key': 'requires_model_builder_handoff',
  'message': 'a model-builder handoff must include handoff_reason',
  'when': {'output_key': 'requires_model_builder_handoff', 'operator': 'is_true', 'value': None},
  'required_key': 'handoff_reason'},
 {'id': 'handoff_target_is_model_builder',
  'template': 'conditional_equals',
  'output_key': 'handoff_target',
  'message': 'handoff_target must be model-builder when a DCF rebuild is required',
  'when': {'output_key': 'requires_model_builder_handoff', 'operator': 'is_true', 'value': None},
  'expected_value': 'model-builder'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_update_coverage_model(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_audit_coverage_model(
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
        required_schema={'audit_summary': 'string',
 'audit_findings': 'string[]',
 'critical_finding_count': 'integer',
 'skip_note': 'boolean',
 'model_audit_ready': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'audit_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'audit_summary must not be empty'},
 {'output_key': 'critical_finding_count',
  'operator': 'equals',
  'value': 0,
  'message': 'critical_finding_count must be zero before the note or final staging'},
 {'output_key': 'model_audit_ready',
  'operator': 'is_true',
  'value': None,
  'message': 'model_audit_ready must be true'}],
        verifier_templates=[{'id': 'no_unresolved_critical_audit_findings',
  'template': 'no_unresolved_findings',
  'output_key': 'audit_findings',
  'message': 'model audit cannot be ready with unresolved critical findings',
  'when': {'output_key': 'model_audit_ready', 'operator': 'is_true', 'value': None},
  'unresolved_terms': ['critical',
                       'blocker',
                       'does not balance',
                       'cash does not tie',
                       'hardcode',
                       'hard-coded',
                       'hardcoded'],
  'resolved_terms': ['resolved', 'fixed', 'closed']}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_repair_model_audit(
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
        required_schema={'repair_summary': 'string', 'repair_actions': 'string[]'},
        optional_schema={},
        verifier_rules=[{'output_key': 'repair_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'repair_summary must not be empty'}],
        verifier_templates=[{'id': 'repair_actions_present',
  'template': 'min_count',
  'output_key': 'repair_actions',
  'message': 'model-audit repair must record at least one repair action',
  'min_count': 1}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_draft_earnings_note(
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
        required_schema={'note_path': 'string',
 'note_headline': 'string',
 'note_includes_variance_table': 'boolean',
 'published_externally': 'boolean',
 'note_ready': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'note_headline',
  'operator': 'truthy',
  'value': None,
  'message': 'note_headline must not be empty'},
 {'output_key': 'note_includes_variance_table',
  'operator': 'is_true',
  'value': None,
  'message': 'note must include the variance table'},
 {'output_key': 'published_externally',
  'operator': 'is_false',
  'value': None,
  'message': 'earnings note must remain unpublished pending senior-analyst sign-off'},
 {'output_key': 'note_ready',
  'operator': 'is_true',
  'value': None,
  'message': 'note_ready must be true'}],
        verifier_templates=[{'id': 'note_path_under_out',
  'template': 'repo_path_policy',
  'output_key': 'note_path',
  'message': 'staged note must be a repository-relative path under out/',
  'required_prefix': 'out/',
  'forbidden_prefixes': []}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def _run_custom_verifier_requirements_update_coverage_model(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_update_coverage_model_variance_rows_cover_required_metrics(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    message = _custom_verifier_requirement_update_coverage_model_handoff_payload_complete_when_required(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: update_coverage_model
# custom_verifier_requirement_id: variance_rows_cover_required_metrics
# template_version: 1
# spec_fingerprint: a2d205752ae86b4bebafaf54afe0dd431b51c74803cbf23a53af5e675d2cb27f
# implementation_version: none
def _custom_verifier_requirement_update_coverage_model_variance_rows_cover_required_metrics(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Require sourced Revenue/GM/EBITDA/EPS rows; otherwise demand exact [UNSOURCED]."""
    _ = state, repo_root
    rows = output.get("variance_rows")
    if not isinstance(rows, list):
        return "variance_rows must be a list of metric records"
    required_metrics = ("revenue", "gm", "ebitda", "eps")
    required_fields = ("actual", "consensus", "prior_estimate", "source")
    trusted_tokens = {
        "factset",
        "daloopa",
        "10-q",
        "10-k",
        "8-k",
        "20-f",
        "6-k",
        "transcript",
    }
    indexed_rows: dict[str, dict] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            return f"variance_rows[{index}] must be an object"
        metric = row.get("metric")
        if not isinstance(metric, str) or not metric.strip():
            return f"variance_rows[{index}].metric must be a non-empty string"
        indexed_rows[metric.strip().lower()] = row
    missing_metrics = [metric for metric in required_metrics if metric not in indexed_rows]
    if missing_metrics:
        return f"variance_rows missing required metrics: {missing_metrics}"
    for metric in required_metrics:
        row = indexed_rows[metric]
        for field_name in required_fields:
            value = row.get(field_name)
            if not isinstance(value, str) or not value.strip():
                return f"{metric} variance row missing {field_name}"
        source = str(row.get("source") or "").strip()
        lowered = source.lower()
        negated = re.search(r"\b(not|no|internal)\b", lowered) is not None
        tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", lowered)
        trusted = (not negated) and any(token in trusted_tokens for token in tokens)
        combined = " ".join(str(row.get(field_name) or "") for field_name in required_fields)
        if not trusted and "[UNSOURCED]" not in combined:
            return f"{metric} variance row is unsourced and missing [UNSOURCED]"
    return None

# custom_verifier_stage_id: update_coverage_model
# custom_verifier_requirement_id: handoff_payload_complete_when_required
# template_version: 1
# spec_fingerprint: d71b17e65ed175176c108df32009e80962df5677faa40ead949e91baee5245cb
# implementation_version: none
def _custom_verifier_requirement_update_coverage_model_handoff_payload_complete_when_required(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Require a complete model-builder payload only when a DCF handoff is flagged."""
    _ = state, repo_root
    if output.get("requires_model_builder_handoff") is not True:
        return None
    payload = output.get("handoff_payload")
    if not isinstance(payload, dict):
        return "handoff_payload must be an object when a model-builder handoff is required"
    required_fields = (
        "ticker",
        "reporting_period",
        "updated_model_path",
        "thesis_change_summary",
    )
    missing = [
        field_name
        for field_name in required_fields
        if not isinstance(payload.get(field_name), str) or not str(payload.get(field_name)).strip()
    ]
    if missing:
        return f"handoff_payload missing required fields: {missing}"
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
