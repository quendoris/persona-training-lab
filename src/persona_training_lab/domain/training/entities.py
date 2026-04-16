from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TrainingRun:
    id: str
    training_config_id: str
    status: str
