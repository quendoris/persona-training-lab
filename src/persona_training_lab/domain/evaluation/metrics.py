from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MetricReport:
    id: str
    evaluation_run_id: str
    profile_match_score: float
