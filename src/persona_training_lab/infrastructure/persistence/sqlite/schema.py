from __future__ import annotations

import sqlite3


def create_minimal_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS ui_preferences (
            id TEXT PRIMARY KEY,
            theme TEXT NULL,
            accent_palette TEXT NULL,
            button_style_preset TEXT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS event_log (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            entity_kind TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            correlation_id TEXT NULL,
            causation_id TEXT NULL,
            payload_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_event_log_entity
        ON event_log(entity_kind, entity_id, occurred_at);
        """
    )
    connection.commit()
