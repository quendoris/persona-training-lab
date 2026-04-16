from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ValidationReport:
    id: str
    dataset_version_id: str
    validation_status: str
