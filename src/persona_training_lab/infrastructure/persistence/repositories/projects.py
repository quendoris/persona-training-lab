from __future__ import annotations

import sqlite3

from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
)


class SQLiteProjectsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)

    def list_projects(self) -> list[dict[str, str]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, title, status
                FROM projects
                ORDER BY updated_at DESC, title ASC
                """
            ).fetchall()
        return [
            {
                "project_id": row["id"],
                "title": row["title"],
                "status": row["status"],
            }
            for row in rows
        ]
