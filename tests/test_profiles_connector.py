from __future__ import annotations

import sqlite3

from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.infrastructure.persistence.repositories.profiles import SQLiteProfilesRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel


def _build_service(connection: sqlite3.Connection) -> ProfilesService:
    repo = SQLiteProfilesRepository(connection)
    return ProfilesService(profiles_repo=repo)


def test_profiles_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_profiles()
    assert rows == []

    vm = ProfilesViewModel(profiles_service=service)
    title, subtitle = vm.header_summary()
    assert title == "Профили пока не созданы"
    assert subtitle == "Профили пока не созданы"


def test_profiles_connector_single_row() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO persona_profiles (id, title, subtitle, status, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "mia_core_v3",
            "Mia core v3 (SQLite)",
            "Реальный профиль из БД",
            "активен",
            "2026-04-26T12:00:00Z",
        ),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_profiles()
    assert len(rows) == 1
    assert rows[0].profile_id == "mia_core_v3"
    assert rows[0].title == "Mia core v3 (SQLite)"

    vm = ProfilesViewModel(profiles_service=service)
    profile = vm.current_profile()
    assert profile.profile_id == "mia_core_v3"
    assert profile.title == "Mia core v3 (SQLite)"
    assert profile.subtitle == "Реальный профиль из БД"
