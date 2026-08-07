from __future__ import annotations


def make_agent_repair_payload(
    *,
    category: str,
    summary: str,
    requirements: list[str] | None = None,
    evidence: list[str] | None = None,
) -> dict[str, object]:
    return {
        "category": _clean_text(category) or "failed",
        "summary": _clean_text(summary) or "Repair is required before the workflow can continue.",
        "requirements": _clean_items(requirements, limit=5),
        "evidence": _clean_items(evidence, limit=3),
    }


def build_default_agent_repair_payload(
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> dict[str, object] | None:
    status = observation.get("status")
    output = observation.get("structured_output") or {}
    summary = _clean_text(observation.get("summary"))

    if verifier_result is not None and (
        not isinstance(verifier_result, dict)
        or verifier_result.get("passed") is not True
    ):
        verifier_message = (
            _clean_text(verifier_result.get("message"))
            if isinstance(verifier_result, dict)
            else ""
        )
        return make_agent_repair_payload(
            category="verifier_failed",
            summary=verifier_message or f"{current_step_id} did not satisfy verifier checks.",
            requirements=[verifier_message] if verifier_message else [],
            evidence=[summary] if summary and summary != verifier_message else [],
        )

    if status == "blocked":
        blocked_reason = _clean_text(_mapping_get(output, "blocked_reason"))
        missing_inputs = _clean_items(_mapping_get(output, "missing_inputs"), limit=5)
        open_questions = _clean_items(_mapping_get(output, "open_questions"), limit=5)
        requirements = missing_inputs or open_questions
        evidence = []
        if summary and summary != blocked_reason:
            evidence.append(summary)
        return make_agent_repair_payload(
            category="blocked",
            summary=blocked_reason or summary or f"{current_step_id} is blocked and needs external input.",
            requirements=requirements,
            evidence=evidence,
        )

    if status in {"failed", "partial"}:
        error_message = _clean_text(_mapping_get(output, "error_message"))
        failed_commands = _clean_items(_mapping_get(output, "failed_commands"), limit=5)
        failing_checks = _clean_items(_mapping_get(output, "failing_checks"), limit=5)
        requirements = failed_commands + failing_checks
        evidence = [item for item in [summary] if item and item != error_message]
        return make_agent_repair_payload(
            category=status,
            summary=error_message or summary or f"{current_step_id} requires repair before retry.",
            requirements=requirements,
            evidence=evidence,
        )

    return None


def _mapping_get(payload, key: str):
    if isinstance(payload, dict):
        return payload.get(key)
    return None


def _clean_text(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _clean_items(value, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for raw in value:
        if len(items) >= limit:
            break
        text = _clean_text(raw)
        if text:
            items.append(text)
    return items
