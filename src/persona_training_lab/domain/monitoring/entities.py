from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ResourceSample:
    id: str
    context_kind: str
    context_id: str
    sampled_at: str
