from __future__ import annotations

import sqlite3

from persona_training_lab.application.ports.event_log import (
    EventLogPort,
    EventRecord,
)
from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
)


class SQLiteEventLogRepository(EventLogPort):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)

    def append(self, record: EventRecord) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO event_log (
                    id, event_type, entity_kind, entity_id,
                    correlation_id, causation_id, payload_json, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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

    def list_recent(self, limit: int = 50) -> list[EventRecord]:
        safe_limit = max(1, min(int(limit), 500))
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, event_type, entity_kind, entity_id,
                       correlation_id, causation_id, payload_json, occurred_at
                FROM event_log
                ORDER BY occurred_at DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            EventRecord(
                id=str(row["id"]),
                event_type=str(row["event_type"]),
                entity_kind=str(row["entity_kind"]),
                entity_id=str(row["entity_id"]),
                correlation_id=(
                    str(row["correlation_id"])
                    if row["correlation_id"] is not None
                    else None
                ),
                causation_id=(
                    str(row["causation_id"])
                    if row["causation_id"] is not None
                    else None
                ),
                payload_json=str(row["payload_json"]),
                occurred_at=str(row["occurred_at"]),
            )
            for row in rows
        ]
