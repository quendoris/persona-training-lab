from __future__ import annotations

import sqlite3


class SQLiteExperimentsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_experiments(self) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT id, title, subtitle, status, updated_at
            FROM experiments
            ORDER BY updated_at DESC, title ASC
            """
        ).fetchall()
        return [
            {
                "experiment_id": row["id"],
                "title": row["title"],
                "subtitle": row["subtitle"],
                "status": row["status"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def create_experiment(self, payload: dict[str, str]) -> None:
        self._connection.execute(
            """
            INSERT INTO experiments (id, title, subtitle, status, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload["id"],
                payload["title"],
                payload["subtitle"],
                payload["status"],
                payload["updated_at"],
            ),
        )
        self._connection.commit()
