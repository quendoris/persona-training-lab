from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SummaryDTO:
    title: str
    subtitle: str | None = None
