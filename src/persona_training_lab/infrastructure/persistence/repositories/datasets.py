from __future__ import annotations

import sqlite3


class SQLiteDatasetsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_datasets(self) -> list[dict[str, str | int]]:
        rows = self._connection.execute(
            """
            SELECT id, title, subtitle, status, record_count, linked_profile, quality_summary, readiness, schema_name
            FROM datasets
            ORDER BY updated_at DESC, title ASC
            """
        ).fetchall()
        return [
            {
                "dataset_id": row["id"],
                "title": row["title"],
                "subtitle": row["subtitle"],
                "status": row["status"],
                "record_count": row["record_count"],
                "linked_profile": row["linked_profile"],
                "quality_summary": row["quality_summary"],
                "readiness": row["readiness"],
                "schema_name": row["schema_name"],
            }
            for row in rows
        ]
