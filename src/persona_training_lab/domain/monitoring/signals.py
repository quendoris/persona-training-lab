from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RiskSignal:
    id: str
    context_kind: str
    context_id: str
    severity: str
    message: str
