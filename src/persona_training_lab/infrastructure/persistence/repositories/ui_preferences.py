from __future__ import annotations

import sqlite3

from persona_training_lab.shared.ids import new_id
from persona_training_lab.shared.time import utc_now_iso


class SQLiteUIPreferencesRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def load(self) -> dict[str, str | None]:
        row = self._connection.execute(
            "SELECT theme, accent_palette, button_style_preset, ui_scale FROM ui_preferences LIMIT 1"
        ).fetchone()
        if row is None:
            return {
                "theme": "velvet",
                "accent_palette": "cyan",
                "button_style_preset": "soft_glow",
                "ui_scale": "auto",
            }
        return {
            "theme": row["theme"],
            "accent_palette": row["accent_palette"],
            "button_style_preset": row["button_style_preset"],
            "ui_scale": row["ui_scale"],
        }

    def save(self, preferences: dict[str, str | None]) -> None:
        row = self._connection.execute("SELECT id FROM ui_preferences LIMIT 1").fetchone()
        now = utc_now_iso()
        if row is None:
            self._connection.execute(
                """
                INSERT INTO ui_preferences (id, theme, accent_palette, button_style_preset, ui_scale, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("uip"),
                    preferences.get("theme"),
                    preferences.get("accent_palette"),
                    preferences.get("button_style_preset"),
                    preferences.get("ui_scale") or "auto",
                    now,
                ),
            )
        else:
            self._connection.execute(
                """
                UPDATE ui_preferences
                SET theme = ?, accent_palette = ?, button_style_preset = ?, ui_scale = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    preferences.get("theme"),
                    preferences.get("accent_palette"),
                    preferences.get("button_style_preset"),
                    preferences.get("ui_scale") or "auto",
                    now,
                    row["id"],
                ),
            )
        self._connection.commit()
