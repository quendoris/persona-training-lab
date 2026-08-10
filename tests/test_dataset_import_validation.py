from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

import pytest

from persona_training_lab.application.datasets.diagnostics import (
    decode_dataset_diagnostic,
)
from persona_training_lab.application.datasets.errors import (
    DatasetServiceError,
    DatasetServiceErrorCode,
)
from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.domain.datasets.statuses import (
    DatasetReadinessStatus,
    DatasetVersionStatus,
)
from persona_training_lab.i18n.deep_audit import DeepSurfaceAudit
from persona_training_lab.infrastructure.persistence.repositories.datasets import (
    SQLiteDatasetsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.viewmodels.datasets import DatasetsViewModel


def _build_service(connection: sqlite3.Connection) -> DatasetsService:
    repo = SQLiteDatasetsRepository(connection)
    return DatasetsService(datasets_repo=repo)


def test_register_missing_file_returns_controlled_error(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    with pytest.raises(DatasetServiceError) as missing_path:
        service.add_dataset_from_path("missing.jsonl")
    assert missing_path.value.code is DatasetServiceErrorCode.FILE_NOT_FOUND
    assert str(missing_path.value) == "file_not_found"

    wrong_format = tmp_path / "dataset.txt"
    wrong_format.write_text("{}\n", encoding="utf-8")
    with pytest.raises(DatasetServiceError) as invalid_format:
        service.add_dataset_from_path(str(wrong_format))
    assert invalid_format.value.code is DatasetServiceErrorCode.ONLY_JSONL

    with pytest.raises(DatasetServiceError) as missing_dataset:
        service.validate_dataset("ds_missing")
    assert missing_dataset.value.code is DatasetServiceErrorCode.NOT_FOUND


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
    assert result.status == DatasetVersionStatus.VALIDATED.value
    assert result.total_rows == 1
    assert result.valid_rows == 1
    assert result.invalid_rows == 0
    preview = service.preview_dataset(created.dataset_id)
    assert preview[0].input_summary == "Привет"
    assert preview[0].quality == "structure_ok"


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
    assert result.status == DatasetVersionStatus.VALIDATED.value
    preview = service.preview_dataset(created.dataset_id)
    assert preview[0].input_summary == "Сделай ответ · контекст"
    assert preview[0].quality == "structure_ok"


def test_approve_valid_dataset_sets_approved_status(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    repo = SQLiteDatasetsRepository(connection)
    service = DatasetsService(datasets_repo=repo)

    dataset_file = tmp_path / "approved.jsonl"
    dataset_file.write_text(
        '{"prompt":"A","response":"B"}\n',
        encoding="utf-8",
    )

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.approve_dataset(created.dataset_id)

    assert result.ok is True
    assert result.code == "approved"
    assert dict(result.values) == {}
    persisted = repo.get_dataset(created.dataset_id)
    assert persisted is not None
    assert persisted["status"] == DatasetVersionStatus.APPROVED.value
    assert persisted["readiness"] == DatasetReadinessStatus.APPROVED.value
    assert persisted["quality_summary"] == ""


def test_validate_invalid_message_role_sets_structure_error(
    tmp_path: Path,
) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    repo = SQLiteDatasetsRepository(connection)
    service = DatasetsService(datasets_repo=repo)

    dataset_file = tmp_path / "bad_role.jsonl"
    dataset_file.write_text(
        '{"messages":[{"role":"user","content":"A"},{"role":"critic","content":"B"},{"role":"assistant","content":"C"}]}\n',
        encoding="utf-8",
    )

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.validate_dataset(created.dataset_id)
    assert result.status == DatasetVersionStatus.STRUCTURE_ERROR.value
    assert result.invalid_rows == 1
    diagnostic = result.errors_preview[0]
    assert diagnostic.code == "invalid_role"
    assert diagnostic.line == 1
    assert diagnostic.values["role"] == "critic"

    persisted = repo.get_dataset(created.dataset_id)
    assert persisted is not None
    decoded = decode_dataset_diagnostic(persisted["validation_errors_preview"])
    assert decoded is not None
    assert decoded.code == "invalid_role"
    assert decoded.line == 1
    assert decoded.values["role"] == "critic"

    preview = service.preview_dataset(created.dataset_id)
    assert preview[0].input_summary == diagnostic
    assert preview[0].quality == "structure_error"


def test_validate_invalid_json_line_sets_structure_error(
    tmp_path: Path,
) -> None:
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
    assert result.status == DatasetVersionStatus.STRUCTURE_ERROR.value
    assert result.valid_rows == 1
    assert result.invalid_rows == 1
    assert result.errors_preview[0].code == "invalid_json"
    assert result.errors_preview[0].line == 2


def test_validate_empty_file_sets_structure_error(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = _build_service(connection)

    dataset_file = tmp_path / "empty.jsonl"
    dataset_file.write_text("", encoding="utf-8")

    created = service.add_dataset_from_path(str(dataset_file))
    result = service.validate_dataset(created.dataset_id)
    assert result.status == DatasetVersionStatus.STRUCTURE_ERROR.value
    assert result.total_rows == 0
    assert result.errors_preview[0].code == "empty_file"
    assert result.errors_preview[0].line is None


def test_repository_persists_validation_result(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    repo = SQLiteDatasetsRepository(connection)
    create_minimal_schema(connection)
    service = DatasetsService(datasets_repo=repo)

    dataset_file = tmp_path / "persist.jsonl"
    dataset_file.write_text(
        '{"prompt":"A","response":"B"}\n',
        encoding="utf-8",
    )

    created = service.add_dataset_from_path(str(dataset_file))
    imported = repo.get_dataset(created.dataset_id)
    assert imported is not None
    assert imported["subtitle"] == ""
    assert imported["status"] == DatasetVersionStatus.IMPORTED.value
    assert imported["quality_summary"] == ""
    assert (
        imported["readiness"]
        == DatasetReadinessStatus.AWAITING_VALIDATION.value
    )

    service.validate_dataset(created.dataset_id)

    persisted = repo.get_dataset(created.dataset_id)
    assert persisted is not None
    assert persisted["status"] == DatasetVersionStatus.VALIDATED.value
    assert persisted["record_count"] == 1
    assert persisted["valid_count"] == 1
    assert persisted["invalid_count"] == 0
    assert persisted["quality_summary"] == ""
    assert persisted["validation_errors_preview"] == ""
    assert (
        persisted["readiness"]
        == DatasetReadinessStatus.AWAITING_AUTHOR_APPROVAL.value
    )

    vm = DatasetsViewModel(datasets_service=service)
    dataset = vm.current_dataset()
    version = vm.current_version()
    assert dataset.subtitle.key == "datasets.subtitle.local_jsonl"
    assert version.status == DatasetVersionStatus.VALIDATED.value
    assert version.status_code == "ready"
    assert vm.status_text(version.status).key == "datasets.status.ready"
    assert version.quality_summary.key == "datasets.quality.ready"
    assert version.preview_rows[0].input_summary == "A"
    assert version.preview_rows[0].quality.key == (
        "datasets.preview.quality.structure_ok"
    )


def test_dataset_repository_defaults_require_machine_semantics(
    tmp_path: Path,
) -> None:
    source = """
def add_dataset(payload):
    hidden = payload.get("status", "Не проверен")
    semantic = payload.get("readiness", "awaiting_validation")
    return hidden, semantic


def update_dataset_validation(payload):
    hidden = payload.get("quality_summary", "Generated quality fallback")
    hidden_diagnostics = payload.get(
        "validation_errors_preview",
        "Generated diagnostic fallback",
    )
    semantic = payload.get("status", "validated")
    return hidden, hidden_diagnostics, semantic


class DatasetServiceErrorCode:
    MACHINE = "file_not_found"
    HUMAN = "Human service code"


class DatasetsService:
    def add_dataset_from_path(self):
        raise ValueError("file_not_found")

    def validate_dataset(self):
        raise DatasetServiceError("Human service error")

    def approve_dataset(self):
        raise DatasetServiceError("not_found")


def preview_surfaces():
    hidden_diagnostic = DatasetDiagnostic("Human diagnostic code")
    hidden_factory = dataset_diagnostic("Human diagnostic factory")
    semantic_diagnostic = dataset_diagnostic("invalid_json")
    hidden_preview = DatasetPreviewRecord(
        "#001",
        "Hidden preview summary",
        "messages",
        "Human preview quality",
    )
    semantic_preview = DatasetPreviewRecord(
        "#002",
        dataset_diagnostic("invalid_json", line=2),
        "messages",
        "structure_error",
    )
    return (
        hidden_diagnostic,
        hidden_factory,
        semantic_diagnostic,
        hidden_preview,
        semantic_preview,
    )
"""
    path = tmp_path / "infrastructure" / "persistence" / "datasets.py"
    visitor = DeepSurfaceAudit(path, display_root=tmp_path)
    visitor.visit(ast.parse(source, filename=str(path)))

    findings = {(item.call, item.text) for item in visitor.literals}
    assert (
        "add_dataset persisted status default",
        "Не проверен",
    ) in findings
    assert (
        "update_dataset_validation persisted quality_summary default",
        "Generated quality fallback",
    ) in findings
    assert (
        "update_dataset_validation persisted validation_errors_preview default",
        "Generated diagnostic fallback",
    ) in findings
    assert (
        "DatasetServiceErrorCode code",
        "Human service code",
    ) in findings
    assert (
        "add_dataset_from_path exception protocol",
        "ValueError",
    ) in findings
    assert (
        "DatasetServiceError code",
        "Human service error",
    ) in findings
    assert (
        "DatasetDiagnostic code",
        "Human diagnostic code",
    ) in findings
    assert (
        "dataset_diagnostic code",
        "Human diagnostic factory",
    ) in findings
    assert (
        "DatasetPreviewRecord input_summary",
        "Hidden preview summary",
    ) in findings
    assert (
        "DatasetPreviewRecord quality",
        "Human preview quality",
    ) in findings
    assert not any(text == "awaiting_validation" for _, text in findings)
    assert not any(text == "validated" for _, text in findings)
    assert not any(text == "file_not_found" for _, text in findings)
    assert not any(text == "not_found" for _, text in findings)
    assert not any(text == "invalid_json" for _, text in findings)
    assert not any(text == "structure_error" for _, text in findings)
