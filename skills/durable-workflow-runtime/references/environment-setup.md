# Environment Setup

Use this file when preparing a local Python environment for:

- normal `bridge.py start` / `bridge.py resume` execution
- importing `workflow-runtime` modules such as `runtime.engine_graphbuilder`
- running runtime regression tests

Unless explicitly marked as a repo-local example, paths below are relative to
`<skill-root>/`.

## Why this matters

This skill depends on Python packages that are not part of the standard
library. If they are missing, normal runtime execution and tests can both fail
before workflow logic even starts.

Typical symptom:

```text
ModuleNotFoundError: No module named 'pydantic_graph'
```

Treat that as an environment setup problem first.

## Required packages

Install the packages from:

```text
<skill-root>/requirements.txt
```

Current requirements include:

- `pydantic`
- `pydantic-graph`
- `pytest`

## Recommended local venv

In this repo, runtime tests currently look for site-packages under the repo
ancestor virtualenv:

```text
/Users/hui.xu/SourceCode/.venv
```

If that venv does not exist yet, create it:

```bash
python -m venv /Users/hui.xu/SourceCode/.venv
```

Then install the runtime requirements:

```bash
/Users/hui.xu/SourceCode/.venv/bin/python -m pip install -r \
  /Users/hui.xu/SourceCode/slm-as-harness/skills/durable-workflow-runtime/requirements.txt
```

## Verify imports

Use the venv Python to confirm the required packages import correctly:

```bash
/Users/hui.xu/SourceCode/.venv/bin/python - <<'PY'
for name in ("pydantic", "pydantic_graph", "pytest"):
    module = __import__(name)
    print(name, module.__file__)
PY
```

## Running the main runtime test file

Run the durable workflow runtime regression suite with the prepared venv:

```bash
PYTHONPATH=/Users/hui.xu/SourceCode/.venv/lib/python3.14/site-packages \
  /Users/hui.xu/SourceCode/.venv/bin/python -m pytest \
  /Users/hui.xu/SourceCode/slm-as-harness/skills/durable-workflow-runtime/tests/test_durable_workflow_runtime.py
```

You can also run a focused subset:

```bash
PYTHONPATH=/Users/hui.xu/SourceCode/.venv/lib/python3.14/site-packages \
  /Users/hui.xu/SourceCode/.venv/bin/python -m pytest \
  /Users/hui.xu/SourceCode/slm-as-harness/skills/durable-workflow-runtime/tests/test_durable_workflow_runtime.py \
  -k 'ios_workflow_engine or workflow_creator_cli_generates_business_workflow_from_spec'
```

## Notes

- Keep environment setup separate from adapter logic. Do not patch
  `skill_host.py` just to compensate for missing local packages.
- `pytest` is listed here because the main runtime regression file is executed
  through pytest in local verification, even though the runtime itself is not a
  pytest plugin.
- If the Python minor version changes, update the `site-packages` segment in
  the example `PYTHONPATH` accordingly.
