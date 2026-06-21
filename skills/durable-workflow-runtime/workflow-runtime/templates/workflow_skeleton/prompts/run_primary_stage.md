You are executing the `run_primary_stage` step of a durable workflow runtime.

Workflow goal:
{{workflow_goal}}

Do the main stage work for this workflow. Follow the step contract exactly.

Return an `Observation` whose `structured_output` matches the success or
failure schema published for this step.
