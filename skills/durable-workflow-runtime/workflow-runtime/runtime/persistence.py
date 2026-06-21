from __future__ import annotations

import json
from pathlib import Path

from runtime.models import RunState


class FileRunStateStore:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)
        self.runs_dir = self.repo_root / ".durable-workflow-runtime" / "runs"

    def _path_for(self, run_id: str) -> Path:
        return self.runs_dir / f"{run_id}.json"

    def save(self, run_state: RunState) -> Path:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        target = self._path_for(run_state.run_id)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(run_state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(target)
        return target

    def load(self, run_id: str) -> RunState | None:
        target = self._path_for(run_id)
        if not target.exists():
            return None
        return RunState.from_dict(json.loads(target.read_text(encoding="utf-8")))
