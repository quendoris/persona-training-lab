from __future__ import annotations

import sqlite3

from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.application.projects.service import ProjectsService
from persona_training_lab.infrastructure.persistence.repositories.projects import SQLiteProjectsRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel


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

    vm = DashboardViewModel(docs_service=DocsService(), projects_service=service)
    label, value, note = vm.stats()[0]
    assert label == "Проекты"
    assert value == "00"
    assert note == "Проекты пока не созданы"


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

    vm = DashboardViewModel(docs_service=DocsService(), projects_service=service)
    label, value, note = vm.stats()[0]
    assert label == "Проекты"
    assert value == "01"
    assert note == "Alpha Persona · активен"
