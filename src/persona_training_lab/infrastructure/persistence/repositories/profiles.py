from __future__ import annotations

import sqlite3


class SQLiteProfilesRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_profiles(self) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT id, title, subtitle, description, communication_style, principles, constraints, notes, status
            FROM persona_profiles
            ORDER BY updated_at DESC, title ASC
            """
        ).fetchall()
        return [
            {
                "profile_id": row["id"],
                "title": row["title"],
                "subtitle": row["subtitle"],
                "description": row["description"],
                "communication_style": row["communication_style"],
                "principles": row["principles"],
                "constraints": row["constraints"],
                "notes": row["notes"],
                "status": row["status"],
            }
            for row in rows
        ]

    def create_profile(self, payload: dict[str, str]) -> None:
        self._connection.execute(
            """
            INSERT INTO persona_profiles (
                id, title, subtitle, description, communication_style, principles, constraints, notes, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("id", ""),
                payload.get("title", ""),
                payload.get("subtitle", ""),
                payload.get("description", ""),
                payload.get("communication_style", ""),
                payload.get("principles", ""),
                payload.get("constraints", ""),
                payload.get("notes", ""),
                payload.get("status", "готов"),
                payload.get("created_at", ""),
                payload.get("updated_at", ""),
            ),
        )
        self._connection.commit()

    def update_profile(self, profile_id: str, payload: dict[str, str]) -> bool:
        cursor = self._connection.execute(
            """
            UPDATE persona_profiles
            SET title = ?,
                subtitle = ?,
                description = ?,
                communication_style = ?,
                principles = ?,
                constraints = ?,
                notes = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.get("title", ""),
                payload.get("subtitle", ""),
                payload.get("description", ""),
                payload.get("communication_style", ""),
                payload.get("principles", ""),
                payload.get("constraints", ""),
                payload.get("notes", ""),
                payload.get("status", "готов"),
                payload.get("updated_at", ""),
                profile_id,
            ),
        )
        self._connection.commit()
        return cursor.rowcount > 0
