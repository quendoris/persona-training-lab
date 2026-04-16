from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TraitDefinition:
    id: str
    canonical_name: str
    trait_type: str
