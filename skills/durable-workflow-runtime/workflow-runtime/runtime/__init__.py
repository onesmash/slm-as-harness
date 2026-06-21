"""Runtime package for the durable workflow runtime."""

from __future__ import annotations

import sys
from pathlib import Path


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / ".venv").exists():
            return candidate
    return current.parents[5]


def _bootstrap_repo_venv() -> None:
    repo_root = _find_repo_root()
    venv_lib = repo_root / ".venv" / "lib"
    if not venv_lib.exists():
        return
    for site_packages in venv_lib.glob("python*/site-packages"):
        site_packages_text = str(site_packages)
        if site_packages_text not in sys.path:
            sys.path.insert(0, site_packages_text)


_bootstrap_repo_venv()
