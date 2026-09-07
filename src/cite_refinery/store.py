from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


_EMPTY_STATE: dict[str, Any] = {
    "version": 1,
    "projects": {},
    "claims": {},
    "evidence": {},
    "audits": {},
    "capabilities": {},
    "implementations": {},
    "artifacts": {},
    "experiments": {},
    "events": [],
}


class JsonStore:
    """Small, auditable persistence layer with atomic writes."""

    def __init__(self, workspace: str | Path = ".cite-refinery") -> None:
        self.workspace = Path(workspace)
        self.path = self.workspace / "state.json"
        self.workspace.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(deepcopy(_EMPTY_STATE))

    def load(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        for key, default in _EMPTY_STATE.items():
            data.setdefault(key, deepcopy(default))
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix="state-", suffix=".json", dir=self.workspace)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, sort_keys=True, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
