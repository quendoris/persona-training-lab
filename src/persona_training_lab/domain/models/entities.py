from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BaseModel:
    id: str
    name: str
    family: str
    version: str
