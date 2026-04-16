from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class EventRecord:
    id: str
    event_type: str
    entity_kind: str
    entity_id: str
    payload_json: str
    occurred_at: str
    correlation_id: str | None = None
    causation_id: str | None = None


class EventLogPort(Protocol):
    def append(self, record: EventRecord) -> None: ...
