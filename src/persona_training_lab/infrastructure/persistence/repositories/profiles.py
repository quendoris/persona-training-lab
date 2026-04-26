from __future__ import annotations

import sqlite3


class SQLiteProfilesRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_profiles(self) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT id, title, subtitle, status
            FROM persona_profiles
            ORDER BY updated_at DESC, title ASC
            """
        ).fetchall()
        return [
            {
                "profile_id": row["id"],
                "title": row["title"],
                "subtitle": row["subtitle"],
                "status": row["status"],
            }
            for row in rows
        ]
