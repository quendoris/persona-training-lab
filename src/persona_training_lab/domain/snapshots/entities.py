from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FreezeSnapshot:
    id: str
    source_training_run_id: str
    status: str
