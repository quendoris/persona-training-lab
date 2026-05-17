from __future__ import annotations

from dataclasses import dataclass
import re
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.ports.repositories import TrainingReadRepositoryPort, TrainingWriteRepositoryPort
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.training.full_backend import LocalFullFineTuneBackend


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
    progress: str = "0"
    artifact_path: str = ""
    error_message: str = ""


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
    full_backend: LocalFullFineTuneBackend | None = None
    marker_backend: Any | None = None  # legacy constructor compatibility; not used by the runtime path

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
                progress=row.get("progress", "0"),
                artifact_path=row.get("artifact_path", ""),
                error_message=row.get("error_message", ""),
            )
            for row in rows
        ]

    def list_training_run_logs(self, run_id: str, limit: int = 200) -> list[str]:
        lister = getattr(self.training_repo, "list_training_logs", None)
        if lister is None:
            return []
        return lister(run_id, limit)

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
            "mode": "Full fine-tune",
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
            progress="0",
            artifact_path="",
            error_message="",
        )

    def _parse_hparams(self, subtitle: str) -> tuple[int, int, float]:
        epochs = 1
        batch_size = 1
        learning_rate = 1e-4
        m = re.search(r"epochs=(\d+)", subtitle)
        if m:
            epochs = max(1, int(m.group(1)))
        m = re.search(r"batch=(\d+)", subtitle)
        if m:
            batch_size = max(1, int(m.group(1)))
        m = re.search(r"lr=([0-9.eE+-]+)", subtitle)
        if m:
            learning_rate = max(1e-8, float(m.group(1)))
        return epochs, batch_size, learning_rate

    def _set_runtime(self, run_id: str, payload: dict[str, str]) -> None:
        updater = getattr(self.training_repo, "update_training_run_runtime", None)
        if updater is not None:
            updater(run_id, payload)

    def _log(self, run_id: str, message: str, level: str = "INFO") -> None:
        logger = getattr(self.training_repo, "add_training_log", None)
        if logger is not None:
            logger(run_id, level, message)

    def start_full_finetune_run(self, run_id: str) -> str:
        get_run = getattr(self.training_repo, "get_training_run", None)
        if get_run is None:
            raise TrainingValidationError("Не удалось запустить обучение")
        run = get_run(run_id)
        if run is None:
            raise TrainingValidationError("Запуск обучения не найден")
        if run.get("status", "") == "Выполняется":
            raise TrainingValidationError("Запуск обучения уже выполняется")
        if run.get("status", "") != "Готов к запуску":
            raise TrainingValidationError("Запуск обучения не готов к старту")
        if self.full_backend is None:
            self._set_runtime(run_id, {"status": "Ошибка", "epoch_progress": run.get("epoch_progress", "—"), "progress": "0", "loss": "—", "speed": "—", "checkpoints_count": "00", "started_at": "", "finished_at": datetime.now(timezone.utc).isoformat(), "artifact_path": "", "error_message": "Training backend не подключён"})
            return "Training backend не подключён"
        if self.local_model_service is None:
            self._set_runtime(run_id, {"status": "Ошибка", "epoch_progress": run.get("epoch_progress", "—"), "progress": "0", "loss": "—", "speed": "—", "checkpoints_count": "00", "started_at": "", "finished_at": datetime.now(timezone.utc).isoformat(), "artifact_path": "", "error_message": "Модель не найдена"})
            return "Модель не найдена"

        epochs, batch_size, learning_rate = self._parse_hparams(run.get("subtitle", ""))
        started_at = datetime.now(timezone.utc).isoformat()
        self._set_runtime(
            run_id,
            {
                "status": "Выполняется",
                "epoch_progress": f"0 / {epochs}",
                "progress": "0",
                "loss": "ожидание метрики",
                "speed": "ожидание метрики",
                "checkpoints_count": "00",
                "started_at": started_at,
                "finished_at": "",
                "artifact_path": "",
                "error_message": "",
            },
        )
        self._log(run_id, "Запуск full fine-tune")
        self._log(run_id, f"Параметры full fine-tune: epochs={epochs}, batch={batch_size}, lr={learning_rate:g}")

        result = self.full_backend.run(
            run_id,
            self.local_model_service.model_path,
            "MIA_SENTINEL_FT_TEST_001",
            "MIA_FINE_TUNE_MARKER_OK_001",
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
        )

        self._log(run_id, result.message)
        self._log(run_id, f"effective max_steps={result.max_steps}, learning_rate={result.learning_rate:g}, trainable_params={result.trainable_params}")
        self._log(run_id, f"initial_loss={result.initial_loss:.6f}, final_loss={result.final_loss:.6f}")
        if result.artifact_path:
            self._log(run_id, f"Artifact saved: {result.artifact_path}")

        is_success = result.status == "Завершено"
        self._set_runtime(
            run_id,
            {
                "status": "Завершено" if is_success else "Ошибка",
                "epoch_progress": f"{epochs} / {epochs}" if is_success else f"0 / {epochs}",
                "progress": "1.0" if is_success else "0",
                "loss": f"{result.final_loss:.6f}" if result.final_loss else "—",
                "speed": "full fine-tune",
                "checkpoints_count": "01" if result.artifact_path else "00",
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "artifact_path": result.artifact_path,
                "error_message": "" if is_success else result.message,
            },
        )
        if not is_success:
            return result.status
        return result.artifact_path

    def start_real_or_skeleton_run(self, run_id: str) -> str:
        return self.start_full_finetune_run(run_id)

    def start_training_run(self, run_id: str) -> None:
        self.start_full_finetune_run(run_id)

    def advance_training_run(self, run_id: str) -> bool:
        run = getattr(self.training_repo, "get_training_run", lambda _id: None)(run_id)
        return bool(run and run.get("status") != "Выполняется")

    def run_marker_finetune_smoke(self, run_id: str) -> tuple[str, str]:
        return "Training backend не подключён", ""
