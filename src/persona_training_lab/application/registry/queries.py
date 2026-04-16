from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RecentEntityQuery:
    limit: int = 10
