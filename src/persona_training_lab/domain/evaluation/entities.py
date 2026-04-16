from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationRun:
    id: str
    freeze_snapshot_id: str
    status: str
