from __future__ import annotations

import sqlite3

from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
)
from persona_training_lab.shared.ids import new_id
from persona_training_lab.shared.time import utc_now_iso


class SQLiteUIPreferencesRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        with self._lock, self._connection:
            columns = {
                row[1]
                for row in self._connection.execute(
                    "PRAGMA table_info(ui_preferences)"
                ).fetchall()
            }
            migrations = {
                "ui_scale": (
                    "ALTER TABLE ui_preferences ADD COLUMN ui_scale "
                    "TEXT NOT NULL DEFAULT 'auto'"
                ),
                "language": (
                    "ALTER TABLE ui_preferences ADD COLUMN language "
                    "TEXT NOT NULL DEFAULT 'ru-RU'"
                ),
            }
            for column, statement in migrations.items():
                if column in columns:
                    continue
                self._connection.execute(statement)

    def load(self) -> dict[str, str | None]:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT theme, accent_palette, button_style_preset, ui_scale, language
                FROM ui_preferences
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return {
                "theme": "velvet",
                "accent_palette": "cyan",
                "button_style_preset": "soft_glow",
                "ui_scale": "auto",
                "language": "ru-RU",
            }
        return {
            "theme": row["theme"],
            "accent_palette": row["accent_palette"],
            "button_style_preset": row["button_style_preset"],
            "ui_scale": row["ui_scale"],
            "language": row["language"],
        }

    def save(self, preferences: dict[str, str | None]) -> None:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT id FROM ui_preferences LIMIT 1"
            ).fetchone()
            now = utc_now_iso()
            values = (
                preferences.get("theme") or "velvet",
                preferences.get("accent_palette") or "cyan",
                preferences.get("button_style_preset") or "soft_glow",
                preferences.get("ui_scale") or "auto",
                preferences.get("language") or "ru-RU",
            )
            if row is None:
                self._connection.execute(
                    """
                    INSERT INTO ui_preferences (
                        id,
                        theme,
                        accent_palette,
                        button_style_preset,
                        ui_scale,
                        language,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (new_id("uip"), *values, now),
                )
            else:
                self._connection.execute(
                    """
                    UPDATE ui_preferences
                    SET theme = ?,
                        accent_palette = ?,
                        button_style_preset = ?,
                        ui_scale = ?,
                        language = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (*values, now, row["id"]),
                )
