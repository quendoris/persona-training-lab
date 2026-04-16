from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TrainingConfig:
    id: str
    base_model_id: str
    persona_profile_id: str
    dataset_version_id: str
    training_mode: str
