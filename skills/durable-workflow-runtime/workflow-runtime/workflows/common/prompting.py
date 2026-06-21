from __future__ import annotations

import re
from pathlib import Path

from runtime.models import PromptEnvelope
from workflows.common.contracts import SkillRoute


PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def resolve_prompt_asset(prompt_asset_path: str | Path, template_context: dict | None = None) -> str:
    path = Path(prompt_asset_path)
    raw_text = path.read_text(encoding="utf-8")
    placeholders = PLACEHOLDER_PATTERN.findall(raw_text)
    if placeholders:
        if template_context is None:
            raise ValueError(f"prompt asset requires template context: {path}")
        rendered = raw_text
        for key in placeholders:
            if key not in template_context:
                raise ValueError(f"missing template key '{key}' for prompt asset: {path}")
            rendered = re.sub(
                r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                str(template_context[key]),
                rendered,
            )
        raw_text = rendered
    prompt = raw_text.strip()
    if not prompt:
        raise ValueError(f"prompt asset is empty: {path}")
    return prompt


def build_prompt_envelope(
    *,
    run_id: str,
    step_id: str,
    prompt_asset_path: str | Path,
    intent: str,
    expected_artifact: str,
    done_when: list[str],
    output_schema: dict,
    failure_schema: dict,
    resume_instructions: str,
    skill_routing: list[SkillRoute] | None = None,
    metadata: dict | None = None,
    template_context: dict | None = None,
) -> PromptEnvelope:
    prompt = resolve_prompt_asset(prompt_asset_path, template_context=template_context)
    prompt = append_skill_routing_to_prompt(prompt, skill_routing or [])
    prompt = append_structured_output_contract_to_prompt(
        prompt,
        output_schema=output_schema,
        failure_schema=failure_schema,
    )
    return PromptEnvelope(
        run_id=run_id,
        step_id=step_id,
        prompt=prompt,
        intent=intent,
        expected_artifact=expected_artifact,
        done_when=done_when,
        output_schema=output_schema,
        failure_schema=failure_schema,
        resume_instructions=resume_instructions,
        metadata=metadata or {},
    )


def append_skill_routing_to_prompt(prompt: str, skill_routing: list[SkillRoute]) -> str:
    block = render_skill_routing_block(skill_routing)
    if not block:
        return prompt
    return f"{prompt}\n\n{block}"


def render_skill_routing_block(skill_routing: list[SkillRoute]) -> str:
    if not skill_routing:
        return ""

    lines = ["本阶段 skill routing："]
    for index, route in enumerate(skill_routing):
        conditions: list[str] = []
        if route.use_when.operations:
            operations = " / ".join(f"`{item}`" for item in route.use_when.operations)
            conditions.append(f"操作命中 {operations}")
        if route.use_when.file_patterns:
            patterns = " / ".join(f"`{item}`" for item in route.use_when.file_patterns)
            conditions.append(f"目标文件命中 {patterns}")
        when_text = " 或 ".join(conditions) if conditions else "命中该 skill 的默认适用场景"
        role = "主技能" if index == 0 else "辅助技能"
        action = "优先使用" if index == 0 else "按需补充使用"
        lines.append(f"- {role}：当 {when_text} 时，{action} `{route.skill}`")
        for note in route.usage_notes:
            lines.append(f"  - 使用说明：{note}")
    return "\n".join(lines)


def append_structured_output_contract_to_prompt(
    prompt: str,
    *,
    output_schema: dict,
    failure_schema: dict,
) -> str:
    block = render_structured_output_contract_block(
        output_schema=output_schema,
        failure_schema=failure_schema,
    )
    if not block:
        return prompt
    return f"{prompt}\n\n{block}"


def render_structured_output_contract_block(*, output_schema: dict, failure_schema: dict) -> str:
    if not output_schema and not failure_schema:
        return ""

    lines = ["本阶段 structured_output 返回契约："]
    if output_schema:
        lines.extend(
            [
                "",
                "当 `status = \"succeeded\"` 时，`structured_output` 必须符合：",
                *render_schema_lines(output_schema),
            ]
        )
    if failure_schema:
        lines.extend(
            [
                "",
                "当 `status` 为 `failed` / `blocked` / `partial` 时，`structured_output` 必须符合：",
                *render_schema_lines(failure_schema),
            ]
        )
    if schema_has_optional_fields(output_schema) or schema_has_optional_fields(failure_schema):
        lines.extend(["", "`?` 表示该字段可选。"])
    return "\n".join(lines)


def render_schema_lines(schema: dict, *, indent: int = 0) -> list[str]:
    lines: list[str] = []
    prefix = "  " * indent
    for key, value in schema.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}- `{key}`: object")
            lines.extend(render_schema_lines(value, indent=indent + 1))
        else:
            lines.append(f"{prefix}- `{key}`: `{value}`")
    return lines


def schema_has_optional_fields(schema: dict) -> bool:
    for value in schema.values():
        if isinstance(value, dict):
            if schema_has_optional_fields(value):
                return True
            continue
        if isinstance(value, str) and value.endswith("?"):
            return True
    return False
