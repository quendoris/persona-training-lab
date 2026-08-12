from __future__ import annotations

import sqlite3

from persona_training_lab.application.projects.service import ProjectsService
from persona_training_lab.infrastructure.persistence.repositories.projects import (
    SQLiteProjectsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.viewmodels.dashboard import (
    DashboardText,
    DashboardViewModel,
)


def _build_service(connection: sqlite3.Connection) -> ProjectsService:
    repo = SQLiteProjectsRepository(connection)
    return ProjectsService(projects_repo=repo)


def test_projects_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_projects()
    assert rows == []

    vm = DashboardViewModel(projects_service=service)
    stat = vm.stats()[0]

    assert stat.label_key == "dashboard.stat.projects"
    assert stat.value.key == "dashboard.raw"
    assert stat.value.values["value"] == "00"
    assert stat.note.key == "dashboard.note.no_projects"


def test_projects_connector_reads_latest_project() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO projects (id, title, status, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        ("prj_001", "Alpha Persona", "активен", "2026-04-26T10:00:00Z"),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_projects()
    assert len(rows) == 1
    assert rows[0].project_id == "prj_001"
    assert rows[0].title == "Alpha Persona"
    assert rows[0].status == "активен"

    vm = DashboardViewModel(projects_service=service)
    stat = vm.stats()[0]

    assert stat.label_key == "dashboard.stat.projects"
    assert stat.value.key == "dashboard.raw"
    assert stat.value.values["value"] == "01"
    assert stat.note.key == "dashboard.note.project_summary"
    assert stat.note.values["title"] == "Alpha Persona"

    status = stat.note.values["status"]
    assert isinstance(status, DashboardText)
    assert status.key == "dashboard.raw"
    assert status.values["value"] == "активен"
