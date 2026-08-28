"""Shared workflow_id validation and module-name mapping.

A workflow's published identifier (``workflow_id``) is the user-facing name:
new workflows use hyphen-separated (kebab-case) ids such as
``co-storm-autonomous-research``. Python module names cannot contain hyphens,
so each workflow's on-disk package and import path use the derived module name
(``co_storm_autonomous_research``). Every runtime consumer that touches the
``workflows/`` directory or imports workflow modules must derive the module
name through :func:`workflow_module_name` instead of assuming the workflow_id
is itself import-safe.
"""

from __future__ import annotations

import re

# Published workflow_id: letters, digits, underscore, or hyphen; must start
# with a letter or underscore. Dots are deliberately excluded because they are
# package separators and would break both import paths and directory lookup.
WORKFLOW_ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")

# Import-safe module/package name: same characters minus the hyphen.
PYTHON_MODULE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def workflow_module_name(workflow_id: str) -> str:
    """Return the import-safe module/package name derived from a workflow_id.

    ``co-storm-autonomous-research`` -> ``co_storm_autonomous_research``.
    A snake_case workflow_id maps to itself, so existing workflows keep their
    on-disk layout when they are renamed to kebab-case.
    """
    return workflow_id.replace("-", "_")


def is_valid_workflow_id(workflow_id: object) -> bool:
    return isinstance(workflow_id, str) and WORKFLOW_ID_PATTERN.fullmatch(workflow_id) is not None
