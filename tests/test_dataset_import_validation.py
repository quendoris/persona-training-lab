from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.infrastructure.persistence.repositories.datasets import SQLiteDatasetsRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema


def _build_service(connection: sqlite3.Connection) -> DatasetsService:
    repo = SQLiteDatasetsRepository(connection)
    return DatasetsService(datasets_repo=repo)


def test_register_missing_file_returns_controlled_error() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    with pytest.raises(ValueError, match="Файл датасета не найден"):
        service.add_dataset_from_path("missing.jsonl")


def test_validate_messages_jsonl_ready(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    dataset_file = tmp_path / "messages.jsonl"
    dataset_file.write_text(
        '{"messages":[{"role":"user","content":"Привет"},{"role":"assistant","content":"Здравствуйте"}]}\n',
        encoding="utf-8",
    )

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.validate_dataset(created.dataset_id)
    assert result.status == "Готов к обучению"
    assert result.total_rows == 1
    assert result.valid_rows == 1
    assert result.invalid_rows == 0


def test_validate_instruction_output_jsonl_ready(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    dataset_file = tmp_path / "instruction.jsonl"
    dataset_file.write_text(
        '{"instruction":"Сделай ответ","input":"контекст","output":"готово"}\n',
        encoding="utf-8",
    )

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.validate_dataset(created.dataset_id)
    assert result.status == "Готов к обучению"


def test_approve_valid_dataset_sets_approved_status(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    repo = SQLiteDatasetsRepository(connection)
    service = DatasetsService(datasets_repo=repo)

    dataset_file = tmp_path / "approved.jsonl"
    dataset_file.write_text('{"prompt":"A","response":"B"}\n', encoding="utf-8")

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.approve_dataset(created.dataset_id)

    assert result.ok is True
    assert result.code == "approved"
    assert dict(result.values) == {}
    persisted = repo.get_dataset(created.dataset_id)
    assert persisted is not None
    assert persisted["status"] == "Одобрен для обучения"
    assert persisted["readiness"] == "Одобрен для обучения"


def test_validate_invalid_message_role_sets_structure_error(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    dataset_file = tmp_path / "bad_role.jsonl"
    dataset_file.write_text(
        '{"messages":[{"role":"user","content":"A"},{"role":"critic","content":"B"},{"role":"assistant","content":"C"}]}\n',
        encoding="utf-8",
    )

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.validate_dataset(created.dataset_id)
    assert result.status == "Ошибка структуры"
    assert result.invalid_rows == 1
    assert "role должен быть system, user или assistant" in "\n".join(result.errors_preview)


def test_validate_invalid_json_line_sets_structure_error(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    dataset_file = tmp_path / "invalid.jsonl"
    dataset_file.write_text(
        '{"prompt":"A","response":"B"}\n{bad json}\n',
        encoding="utf-8",
    )

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.validate_dataset(created.dataset_id)
    assert result.status == "Ошибка структуры"
    assert result.valid_rows == 1
    assert result.invalid_rows == 1
    assert "невалидный JSON" in "\n".join(result.errors_preview)


def test_validate_empty_file_sets_structure_error(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    dataset_file = tmp_path / "empty.jsonl"
    dataset_file.write_text("", encoding="utf-8")

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.validate_dataset(created.dataset_id)
    assert result.status == "Ошибка структуры"
    assert result.total_rows == 0


def test_repository_persists_validation_result(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    repo = SQLiteDatasetsRepository(connection)
    create_minimal_schema(connection)
    service = DatasetsService(datasets_repo=repo)

    dataset_file = tmp_path / "persist.jsonl"
    dataset_file.write_text('{"prompt":"A","response":"B"}\n', encoding="utf-8")

    created = service.add_dataset_from_path(str(dataset_file))
    service.validate_dataset(created.dataset_id)

    persisted = repo.get_dataset(created.dataset_id)
    assert persisted is not None
    assert persisted["status"] == "Готов к обучению"
    assert persisted["record_count"] == 1
    assert persisted["valid_count"] == 1
    assert persisted["invalid_count"] == 0
    assert persisted["readiness"] == "Ожидает одобрение автора"
