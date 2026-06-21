from __future__ import annotations

from runtime.errors import WorkflowExecutionError


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


def validate_schema_value(value, schema, field_name: str) -> None:
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            raise WorkflowExecutionError(f"{field_name} must be an object")
        for key, child_schema in schema.items():
            optional = isinstance(child_schema, str) and child_schema.endswith("?")
            if key not in value:
                if optional:
                    continue
                raise WorkflowExecutionError(f"{field_name}.{key} is required")
            validate_schema_value(value[key], child_schema, f"{field_name}.{key}")
        return
    if not isinstance(schema, str):
        return

    optional = schema.endswith("?")
    schema_name = schema[:-1] if optional else schema
    if value is None:
        if optional:
            return
        raise WorkflowExecutionError(f"{field_name} must not be null")

    if schema_name.endswith("[]"):
        if not isinstance(value, list):
            raise WorkflowExecutionError(f"{field_name} must be a list")
        item_schema = schema_name[:-2]
        for index, item in enumerate(value):
            validate_schema_value(item, item_schema, f"{field_name}[{index}]")
        return

    validators = {
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
    }
    validator = validators.get(schema_name)
    if validator is None:
        return
    if not validator(value):
        raise WorkflowExecutionError(f"{field_name} does not match schema {schema_name}")
