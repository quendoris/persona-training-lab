from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PersonaProfile:
    id: str
    name: str
    version: str
    summary: str
