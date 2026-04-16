from __future__ import annotations

import sqlite3

from persona_training_lab.application.ports.event_log import EventLogPort, EventRecord


class SQLiteEventLogRepository(EventLogPort):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def append(self, record: EventRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO event_log (
                id, event_type, entity_kind, entity_id,
                correlation_id, causation_id, payload_json, occurred_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.event_type,
                record.entity_kind,
                record.entity_id,
                record.correlation_id,
                record.causation_id,
                record.payload_json,
                record.occurred_at,
            ),
        )
        self._connection.commit()
