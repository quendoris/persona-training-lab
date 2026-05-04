from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
from persona_training_lab.application.training.runtime import DeterministicTrainingRunner

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.ports.repositories import TrainingReadRepositoryPort, TrainingWriteRepositoryPort
from persona_training_lab.application.profiles.service import ProfilesService


@dataclass(slots=True, frozen=True)
class TrainingRunSummary:
    run_id: str
    title: str
    subtitle: str
    status: str
    base_model: str
    profile: str
    dataset_version: str
    mode: str
    epoch_progress: str
    loss: str
    speed: str
    checkpoints_count: str


@dataclass(slots=True, frozen=True)
class TrainingProfileOption:
    profile_id: str
    title: str


@dataclass(slots=True, frozen=True)
class TrainingDatasetOption:
    dataset_id: str
    title: str
    status: str


class TrainingConfigurationError(ValueError):
    pass


class TrainingValidationError(ValueError):
    pass


@dataclass(slots=True)
class TrainingService:
    training_repo: TrainingReadRepositoryPort | TrainingWriteRepositoryPort
    profiles_service: ProfilesService | None = None
    datasets_service: DatasetsService | None = None
    local_model_service: LocalModelService | None = None
    runner: DeterministicTrainingRunner | None = None

    def list_training_runs(self) -> list[TrainingRunSummary]:
        rows = self.training_repo.list_training_runs()
        return [
            TrainingRunSummary(
                run_id=row.get("run_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                status=row.get("status", ""),
                base_model=row.get("base_model", ""),
                profile=row.get("profile", ""),
                dataset_version=row.get("dataset_version", ""),
                mode=row.get("mode", ""),
                epoch_progress=row.get("epoch_progress", ""),
                loss=row.get("loss", ""),
                speed=row.get("speed", ""),
                checkpoints_count=row.get("checkpoints_count", ""),
            )
            for row in rows
        ]

    def start_training_run(self, run_id: str) -> None:
        repo = self.training_repo
        get_run = getattr(repo, "get_training_run", None)
        if get_run is None:
            raise TrainingValidationError("Не удалось запустить обучение")
        row = get_run(run_id)
        if row is None:
            raise TrainingValidationError("Запуск обучения не найден")
        status = row.get("status", "")
        if status == "Выполняется":
            raise TrainingValidationError("Запуск обучения уже выполняется")
        if status != "Готов к запуску":
            raise TrainingValidationError("Запуск обучения не готов к старту")
        runner = self.runner or DeterministicTrainingRunner()
        self.runner = runner
        event = runner.start(run_id)
        self._persist_runner_event(event, started_at=datetime.now(timezone.utc).isoformat())

    def advance_training_run(self, run_id: str) -> bool:
        if self.runner is None:
            return False
        event = self.runner.step(run_id)
        self._persist_runner_event(
            event,
            finished_at=datetime.now(timezone.utc).isoformat() if event.finished else "",
        )
        return event.finished

    def list_training_run_logs(self, run_id: str, limit: int = 200) -> list[str]:
        lister = getattr(self.training_repo, "list_training_logs", None)
        if lister is None:
            return []
        return lister(run_id, limit)

    def _persist_runner_event(self, event, *, started_at: str = "", finished_at: str = "") -> None:
        updater = getattr(self.training_repo, "update_training_run_runtime", None)
        logger = getattr(self.training_repo, "add_training_log", None)
        if updater is None or logger is None:
            raise TrainingValidationError("Не удалось запустить обучение")
        updater(
            event.run_id,
            {
                "status": event.status,
                "epoch_progress": event.epoch_progress,
                "progress": str(event.progress),
                "loss": event.loss,
                "speed": event.speed,
                "checkpoints_count": "01" if event.finished else "00",
                "started_at": started_at,
                "finished_at": finished_at,
            },
        )
        logger(event.run_id, "INFO", event.message)

    def list_profile_options(self) -> list[TrainingProfileOption]:
        if self.profiles_service is None:
            return []
        return [
            TrainingProfileOption(profile_id=item.profile_id, title=item.title)
            for item in self.profiles_service.list_profiles()
        ]

    def list_dataset_options(self) -> list[TrainingDatasetOption]:
        if self.datasets_service is None:
            return []
        return [
            TrainingDatasetOption(dataset_id=item.dataset_id, title=item.title, status=item.status)
            for item in self.datasets_service.list_datasets()
        ]

    def create_training_run(
        self,
        *,
        title: str,
        profile_id: str,
        dataset_id: str,
        base_model: str,
        epochs: int,
        batch_size: int,
        learning_rate: float,
    ) -> TrainingRunSummary:
        if epochs <= 0 or batch_size <= 0 or learning_rate <= 0:
            raise TrainingValidationError("Проверьте гиперпараметры: epochs, batch size и learning rate должны быть больше 0")

        profiles = self.list_profile_options()
        selected_profile = next((item for item in profiles if item.profile_id == profile_id), None)
        if selected_profile is None:
            raise TrainingConfigurationError("Сначала создайте профиль личности")

        datasets = self.list_dataset_options()
        selected_dataset = next((item for item in datasets if item.dataset_id == dataset_id), None)
        if selected_dataset is None or selected_dataset.status != "Готов к обучению":
            raise TrainingConfigurationError("Сначала добавьте и проверьте датасет")

        if self.local_model_service is None:
            raise TrainingConfigurationError("Сначала проверьте локальную модель")
        model_probe = self.local_model_service.probe_model_files()
        if model_probe.status != "Модель найдена":
            raise TrainingConfigurationError("Сначала проверьте локальную модель")

        run_id = f"trn_{uuid4().hex[:8]}"
        normalized_title = title.strip() or f"Training run {run_id}"
        payload = {
            "id": run_id,
            "title": normalized_title,
            "subtitle": (
                f"{selected_profile.title} · {selected_dataset.title} · {base_model.strip()} · "
                f"epochs={epochs}, batch={batch_size}, lr={learning_rate:g}"
            ),
            "status": "Готов к запуску",
            "base_model": base_model.strip() or self.local_model_service.model_name,
            "profile": selected_profile.title,
            "dataset_version": selected_dataset.title,
            "mode": "Persona Imprint",
            "epoch_progress": f"0 / {epochs}",
            "loss": "—",
            "speed": "—",
            "checkpoints_count": "00",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        create_method = getattr(self.training_repo, "create_training_run", None)
        if create_method is None:
            raise RuntimeError("Training write repository is not configured")
        create_method(payload)
        return TrainingRunSummary(
            run_id=payload["id"],
            title=payload["title"],
            subtitle=payload["subtitle"],
            status=payload["status"],
            base_model=payload["base_model"],
            profile=payload["profile"],
            dataset_version=payload["dataset_version"],
            mode=payload["mode"],
            epoch_progress=payload["epoch_progress"],
            loss=payload["loss"],
            speed=payload["speed"],
            checkpoints_count=payload["checkpoints_count"],
        )
