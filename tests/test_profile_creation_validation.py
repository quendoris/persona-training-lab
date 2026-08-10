from __future__ import annotations

import sqlite3

from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.infrastructure.persistence.repositories.profiles import (
    SQLiteProfilesRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def _build_service(connection: sqlite3.Connection) -> ProfilesService:
    return ProfilesService(profiles_repo=SQLiteProfilesRepository(connection))


def test_create_profile_requires_structural_fields() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    result, created = service.create_profile(
        title="Core",
        description="Описание",
        communication_style="",
        principles="Принцип",
        constraints="Ограничение",
        notes="",
    )

    assert result.ok is False
    assert result.code == "communication_style_required"
    assert created is None


def test_create_profile_persists_complete_profile() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    repo = SQLiteProfilesRepository(connection)
    service = ProfilesService(profiles_repo=repo)

    result, created = service.create_profile(
        title="Core",
        description="Описание личности",
        communication_style="Тёплый прямой стиль",
        principles="Принцип 1\nПринцип 2",
        constraints="Не терять ядро\nНе ломать стиль",
        notes="Заметка",
    )

    assert result.ok is True
    assert result.code == "created"
    assert created is not None
    rows = repo.list_profiles()
    assert len(rows) == 1
    assert rows[0]["title"] == "Core"
    assert rows[0]["communication_style"] == "Тёплый прямой стиль"
    assert rows[0]["principles"] == "Принцип 1\nПринцип 2"
    assert rows[0]["constraints"] == "Не терять ядро\nНе ломать стиль"
    assert rows[0]["status"] == "ready"


def test_update_profile_requires_existing_profile_and_structural_fields() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    create_result, created = service.create_profile(
        title="Core",
        description="Описание личности",
        communication_style="Стиль",
        principles="Принцип",
        constraints="Ограничение",
        notes="",
    )
    assert create_result.ok is True
    assert created is not None

    invalid_result = service.update_profile(
        profile_id=created.profile_id,
        title="Core v2",
        description="Новое описание",
        communication_style="Стиль",
        principles="",
        constraints="Ограничение",
        notes="",
    )

    assert invalid_result.ok is False
    assert invalid_result.code == "principles_required"

    update_result = service.update_profile(
        profile_id=created.profile_id,
        title="Core v2",
        description="Новое описание",
        communication_style="Стиль",
        principles="Новый принцип",
        constraints="Ограничение",
        notes="",
    )

    assert update_result.ok is True
    assert update_result.code == "updated"
