from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Dataset:
    id: str
    name: str


@dataclass(slots=True, frozen=True)
class DatasetVersion:
    id: str
    dataset_id: str
    version: str
    status: str
