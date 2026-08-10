from __future__ import annotations

import sqlite3

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    ModelProbeResult,
)
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.infrastructure.persistence.repositories.datasets import (
    SQLiteDatasetsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.profiles import (
    SQLiteProfilesRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.training import (
    SQLiteTrainingRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


class _ReadyProbe:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        return ModelProbeResult(
            status="Модель найдена",
            details=f"ok: {model_path}",
        )

    def check_inference_backend(self, model_path: str) -> InferenceProbeResult:
        return InferenceProbeResult(
            message="Inference backend пока не подключён"
        )


def _build_profiles_service(connection: sqlite3.Connection) -> ProfilesService:
    return ProfilesService(profiles_repo=SQLiteProfilesRepository(connection))


def test_create_profile_success() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_profiles_service(connection)
    result, created = service.create_profile(
        title="Mia v1",
        description="Основная цель личности",
        communication_style="Тёплый и спокойный",
        principles="Бережность",
        constraints="Не уходить в холод",
        notes="Черновик",
    )

    assert result.ok is True
    assert result.code == "created"
    assert created is not None
    assert created.status == "ready"
    rows = service.list_profiles()
    assert len(rows) == 1
    assert rows[0].title == "Mia v1"
    assert rows[0].status == "ready"


def test_create_profile_with_empty_title_validation_error() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_profiles_service(connection)
    result, created = service.create_profile(
        title="   ",
        description="Основная цель личности",
        communication_style="Тёплый и спокойный",
        principles="Бережность",
        constraints="Не уходить в холод",
        notes="Черновик",
    )

    assert result.ok is False
    assert result.code == "title_required"
    assert created is None


def test_update_profile_success() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_profiles_service(connection)
    created_result, created = service.create_profile(
        title="Mia v1",
        description="Основная цель личности",
        communication_style="Тёплый и спокойный",
        principles="Бережность",
        constraints="Не уходить в холод",
        notes="Черновик",
    )
    assert created_result.ok is True
    assert created is not None

    update_result = service.update_profile(
        profile_id=created.profile_id,
        title="Mia v2",
        description="Обновлённая цель",
        communication_style="Спокойный и точный",
        principles="Честность",
        constraints="Не терять мягкость",
        notes="Обновлено",
    )
    assert update_result.ok is True
    assert update_result.code == "updated"

    rows = service.list_profiles()
    assert rows[0].title == "Mia v2"
    assert rows[0].description == "Обновлённая цель"
    assert rows[0].status == "ready"


def test_repository_persists_created_profile() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    repo = SQLiteProfilesRepository(connection)
    repo.create_profile(
        {
            "id": "prf_repo_1",
            "title": "Repo profile",
            "subtitle": "Repo subtitle",
            "description": "Repo description",
            "communication_style": "Repo style",
            "principles": "Repo principles",
            "constraints": "Repo constraints",
            "notes": "Repo notes",
            "created_at": "2026-04-27T00:00:00Z",
            "updated_at": "2026-04-27T00:00:00Z",
        }
    )

    rows = repo.list_profiles()
    assert len(rows) == 1
    assert rows[0]["profile_id"] == "prf_repo_1"
    assert rows[0]["description"] == "Repo description"
    assert rows[0]["status"] == "ready"


def test_profiles_viewmodel_refresh_sees_created_profile() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_profiles_service(connection)
    vm = ProfilesViewModel(profiles_service=service)
    assert vm.current_profile().profile_id == "profiles_empty"

    ok, legacy = vm.create_profile(
        title="VM profile",
        description="Описание VM",
        communication_style="Тёплый",
        principles="Бережность",
        constraints="Не давить",
        notes="Заметка",
    )
    assert ok is True
    assert legacy == "Профиль личности создан"
    assert vm.current_message() is not None
    assert vm.current_message().key == "profiles.message.created"
    assert vm.current_profile().title == "VM profile"
    assert vm.current_profile().status_code == "ready"

    ok, legacy = vm.update_current_profile(
        title="VM profile v2",
        description="Обновлённое описание VM",
        communication_style="Тёплый и точный",
        principles="Бережность\nЧестность",
        constraints="Не давить\nНе терять ядро",
        notes="Обновлённая заметка",
    )
    assert ok is True
    assert legacy == "Профиль личности обновлён"
    assert vm.current_message() is not None
    assert vm.current_message().key == "profiles.message.updated"
    assert vm.current_profile().title == "VM profile v2"
    assert vm.current_profile().status_code == "ready"

    rows = service.list_profiles()
    assert len(rows) == 1
    assert rows[0].title == "VM profile v2"
    assert rows[0].status == "ready"


def test_training_viewmodel_profile_blocker_disappears_when_profile_exists() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    profiles_service = _build_profiles_service(connection)
    datasets_service = DatasetsService(
        datasets_repo=SQLiteDatasetsRepository(connection)
    )
    training_service = TrainingService(
        training_repo=SQLiteTrainingRepository(connection),
        profiles_service=profiles_service,
        datasets_service=datasets_service,
        local_model_service=LocalModelService(probe_provider=_ReadyProbe()),
    )

    vm_no_profiles = TrainingViewModel(training_service=training_service)
    assert vm_no_profiles.profile_choices == ()

    result, created = profiles_service.create_profile(
        title="Train profile",
        description="Описание",
        communication_style="Тёплый",
        principles="Бережность",
        constraints="Не давить",
        notes="",
    )
    assert result.ok is True
    assert created is not None

    vm_with_profile = TrainingViewModel(training_service=training_service)
    assert len(vm_with_profile.profile_choices) == 1
    assert vm_with_profile.profile_choices[0].title == "Train profile"
