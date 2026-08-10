from __future__ import annotations

import sqlite3

from persona_training_lab.application.agents.service import AgentsService
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.infrastructure.persistence.repositories.agents import SQLiteAgentsRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel


def _build_service(connection: sqlite3.Connection) -> AgentsService:
    repo = SQLiteAgentsRepository(connection)
    return AgentsService(agents_repo=repo)


def test_agents_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_agents()
    assert rows == []

    vm = AgentsViewModel(agents_service=service)
    title, subtitle = vm.header_summary()
    assert title == "Агенты"
    assert "Рабочий центр версий" in subtitle

    current = vm.current_agent()
    assert isinstance(current.title, UserMessage)
    assert current.title.key == "agents.overview.empty.title"
    assert vm.agents()[0][1] == "Системные роли готовы"
    assert any(role.role_id == "version_navigator" for role in vm.roles())

    base = vm.version_nodes()[0]
    assert isinstance(base.title, UserMessage)
    assert base.title.key == "agents.node.title.base_model"
    assert base.title.values["label"] == "—"


def test_agents_connector_single_row() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO agents (id, title, subtitle, status, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "agt_001",
            "Mia Runtime Agent",
            "Реальный агент из БД",
            "готов",
            "2026-04-26T14:00:00Z",
        ),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_agents()
    assert len(rows) == 1
    assert rows[0].agent_id == "agt_001"
    assert rows[0].title == "Mia Runtime Agent"

    vm = AgentsViewModel(agents_service=service)
    agent = vm.current_agent()
    assert agent.agent_id == "agt_001"
    assert agent.title == "Mia Runtime Agent"
    assert agent.subtitle == "Реальный агент из БД"
