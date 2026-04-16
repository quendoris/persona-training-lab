from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EventEnvelope:
    event_type: str
    entity_kind: str
    entity_id: str
    payload_json: str
    occurred_at: str
