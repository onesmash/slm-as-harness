from __future__ import annotations

import math
from typing import Any

from runtime.errors import SchemaValidationError, WorkflowExecutionError


_SCALAR_SCHEMA_TYPES = {"string", "boolean", "integer", "number", "object"}
_SCHEMA_DESCRIPTOR_KEYS = {
    "type",
    "items",
    "properties",
    "required",
    "additional_properties",
}


def validate_workflow_input(request, input_contract) -> None:
    validate_schema_value(request.task_input, input_contract.task_input_schema, "task_input")
    validate_schema_value(request.context, input_contract.context_schema, "context")
    validate_schema_value(request.constraints, input_contract.constraints_schema, "constraints")


def validate_observation_against_contract(observation, step_contract) -> None:
    schema = (
        step_contract.output_schema
        if observation.status == "succeeded"
        else step_contract.failure_schema
    )
    if schema:
        validate_schema_value(
            observation.structured_output,
            schema,
            "structured_output",
        )


def validate_schema_value(value: Any, schema: Any, field_name: str) -> None:
    """Validate the runtime's small, explicit schema vocabulary.

    A mapping normally describes an object whose keys are the declared fields.
    Descriptor mappings support nested arrays/objects without making the
    runtime depend on a full JSON Schema implementation.
    """

    _validate_schema_value(value, schema, field_name, required=True)


def _validate_schema_value(value: Any, schema: Any, field_name: str, *, required: bool) -> None:
    if isinstance(schema, dict):
        if _is_schema_descriptor(schema):
            _validate_descriptor(value, schema, field_name, required=required)
            return
        if not isinstance(value, dict):
            _schema_error(field_name, "object", value, f"{field_name} must be an object")
        for key, child_schema in schema.items():
            if not isinstance(key, str) or not key.strip():
                _schema_error(field_name, "object field name", key, f"{field_name} contains an invalid field name")
            child_optional = _schema_is_optional(child_schema)
            if key not in value:
                if child_optional:
                    continue
                _schema_error(
                    f"{field_name}.{key}",
                    _schema_display(child_schema),
                    None,
                    f"{field_name}.{key} is required",
                )
            _validate_schema_value(
                value[key],
                _schema_without_optional_marker(child_schema),
                f"{field_name}.{key}",
                required=not child_optional,
            )
        return

    if not isinstance(schema, str):
        _schema_error(
            field_name,
            "supported schema type",
            schema,
            f"{field_name} uses an unsupported schema declaration",
        )

    optional = schema.endswith("?")
    schema_name = schema[:-1] if optional else schema
    if value is None:
        if optional or not required:
            return
        _schema_error(field_name, schema_name, value, f"{field_name} must not be null")

    if schema_name.endswith("[]"):
        if schema_name.count("[]") != 1:
            _schema_error(field_name, schema_name, value, f"{field_name} uses an unsupported array schema")
        if not isinstance(value, list):
            _schema_error(field_name, schema_name, value, f"{field_name} must be a list")
        item_schema = schema_name[:-2]
        if item_schema not in _SCALAR_SCHEMA_TYPES:
            _schema_error(
                field_name,
                schema_name,
                value,
                f"{field_name} uses an unsupported item schema type: {item_schema}",
            )
        for index, item in enumerate(value):
            _validate_schema_value(item, item_schema, f"{field_name}[{index}]", required=True)
        return

    if schema_name not in _SCALAR_SCHEMA_TYPES:
        _schema_error(
            field_name,
            schema_name,
            value,
            f"{field_name} uses unsupported schema type {schema_name!r}",
        )
    if not _value_matches_schema_type(value, schema_name):
        _schema_error(
            field_name,
            schema_name,
            value,
            f"{field_name} does not match schema {schema_name}",
        )


def _validate_descriptor(value: Any, schema: dict, field_name: str, *, required: bool) -> None:
    schema_type = schema.get("type")
    if not isinstance(schema_type, str) or not schema_type.strip():
        _schema_error(field_name, "descriptor type", schema_type, f"{field_name} descriptor requires a type")
    schema_type = schema_type.strip()
    if schema_type == "array":
        if "items" not in schema:
            _schema_error(field_name, "array items", schema, f"{field_name} array descriptor requires items")
        if not isinstance(value, list):
            _schema_error(field_name, "array", value, f"{field_name} must be a list")
        for index, item in enumerate(value):
            _validate_schema_value(item, schema["items"], f"{field_name}[{index}]", required=True)
        return
    if schema_type == "object":
        if not isinstance(value, dict):
            _schema_error(field_name, "object", value, f"{field_name} must be an object")
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            _schema_error(field_name, "object properties", properties, f"{field_name}.properties must be an object")
        required_fields = schema.get("required")
        if required_fields is None:
            required_fields = list(properties)
        if not isinstance(required_fields, list) or any(not isinstance(item, str) for item in required_fields):
            _schema_error(field_name, "required field list", required_fields, f"{field_name}.required must be a string list")
        for key, child_schema in properties.items():
            if key not in value:
                if key in required_fields:
                    _schema_error(f"{field_name}.{key}", _schema_display(child_schema), None, f"{field_name}.{key} is required")
                continue
            _validate_schema_value(value[key], child_schema, f"{field_name}.{key}", required=key in required_fields)
        additional_properties = schema.get("additional_properties", True)
        if not isinstance(additional_properties, bool):
            _schema_error(field_name, "boolean", additional_properties, f"{field_name}.additional_properties must be boolean")
        if additional_properties is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                _schema_error(field_name, "declared object fields", unknown, f"{field_name} has unknown fields: {', '.join(unknown)}")
        return
    if schema_type not in _SCALAR_SCHEMA_TYPES - {"object"}:
        _schema_error(field_name, "supported descriptor type", schema_type, f"{field_name} uses unsupported schema type {schema_type!r}")
    _validate_schema_value(value, schema_type, field_name, required=required)


def _is_schema_descriptor(schema: dict) -> bool:
    return "type" in schema and set(schema).issubset(_SCHEMA_DESCRIPTOR_KEYS)


def _schema_is_optional(schema: Any) -> bool:
    return isinstance(schema, str) and schema.endswith("?")


def _schema_without_optional_marker(schema: Any) -> Any:
    if _schema_is_optional(schema):
        return schema[:-1]
    return schema


def _schema_display(schema: Any) -> str:
    if isinstance(schema, str):
        return schema
    if isinstance(schema, dict):
        return "object descriptor"
    return type(schema).__name__


def _value_matches_schema_type(value: Any, schema_name: str) -> bool:
    if schema_name == "string":
        return isinstance(value, str)
    if schema_name == "boolean":
        return isinstance(value, bool)
    if schema_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_name == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and (not isinstance(value, float) or math.isfinite(value))
        )
    if schema_name == "object":
        return isinstance(value, dict)
    return False


def _schema_error(field_name: str, expected: str, value: Any, message: str) -> None:
    actual = type(value).__name__
    raise SchemaValidationError(
        message,
        path=field_name,
        expected=expected,
        actual=actual,
        source="workflow_contract",
        repairable=False,
    )
