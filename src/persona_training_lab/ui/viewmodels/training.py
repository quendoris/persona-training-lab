from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.training.service import (
    TrainingConfigurationError,
    TrainingService,
    TrainingValidationError,
)


@dataclass(slots=True, frozen=True)
class TrainingMetric:
    title: str
    value: str
    note: str


@dataclass(slots=True, frozen=True)
class CheckpointView:
    name: str
    note: str
    highlighted: bool = False


@dataclass(slots=True, frozen=True)
class PersonalityVersionView:
    title: str
    status: str
    note: str


@dataclass(slots=True, frozen=True)
class TrainingProfileChoice:
    profile_id: str
    title: str


@dataclass(slots=True, frozen=True)
class TrainingDatasetChoice:
    dataset_id: str
    title: str
    status: str


@dataclass(slots=True)
class TrainingViewModel:
    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
    local_model_service: LocalModelService | None = None
    title: str = "Обучение"
    subtitle: str = "Обучение пока не запускалось"
    status: str = "ожидание"
    selected_objects: tuple[tuple[str, str], ...] = (
        ("Базовая модель", "—"),
        ("Профиль", "—"),
        ("Версия датасета", "—"),
        ("Режим", "—"),
    )
    stat_cards: tuple[TrainingMetric, ...] = (
        TrainingMetric("Эпоха", "—", "Обучение пока не запускалось"),
        TrainingMetric("Loss", "—", "Обучение пока не запускалось"),
        TrainingMetric("Скорость", "—", "Обучение пока не запускалось"),
        TrainingMetric("Чекпоинты", "00", "Обучение пока не запускалось"),
    )
    checkpoints: tuple[CheckpointView, ...] = (
        CheckpointView("Чекпоинты и версии личности", "Чекпоинты и версии личности пока не созданы"),
    )
    personality_versions: tuple[PersonalityVersionView, ...] = (
        PersonalityVersionView("Ожидание версий", "пусто", "Версии личности пока не созданы"),
    )
    versions_status_message: str = "Версии личности пока не созданы"
    logs: tuple[str, ...] = (
        "[—] Обучение пока не запускалось",
    )
    monitor_rows: tuple[tuple[str, int, str], ...] = (
        ("Нагрузка GPU", 0, "нет активного запуска"),
        ("Видеопамять", 0, "нет активного запуска"),
        ("Память RAM", 0, "нет активного запуска"),
    )
    risk_title: str = "Статус"
    risk_body: str = "Обучение пока не запускалось"
    next_step: str = "Выберите профиль и датасет, затем запустите обучение."
    local_model_name: str = "Qwen3.5-0.8B"
    local_model_path: str = "models/qwen3.5-0.8b"
    local_model_status: str = "Модель не проверялась"
    local_model_note: str = "Проверка файлов модели выполняется по запросу."
    local_inference_status: str = ""
    inference_prompt: str = "MIA_SENTINEL_FT_TEST_001"
    inference_response: str = ""
    inference_in_progress: bool = False
    creation_message: str = ""
    profile_choices: tuple[TrainingProfileChoice, ...] = ()
    dataset_choices: tuple[TrainingDatasetChoice, ...] = ()
    current_run_id: str = ""
    can_start_run: bool = False

    def __post_init__(self) -> None:
        self._apply_training_connector()
        self._apply_model_versions_connector()
        self._sync_local_model_info()
        self._sync_creation_choices()

    def _sync_local_model_info(self) -> None:
        if self.local_model_service is None:
            return
        self.local_model_name = self.local_model_service.model_name
        self.local_model_path = self.local_model_service.model_path

    def _apply_training_connector(self) -> None:
        if self.training_service is None:
            return

        try:
            runs = self.training_service.list_training_runs()
        except Exception:
            self.title = "Обучение"
            self.subtitle = "Не удалось загрузить запуски обучения"
            self.status = "ошибка"
            self.logs = ("[—] Не удалось загрузить запуски обучения",)
            self.risk_title = "Статус"
            self.risk_body = "Не удалось загрузить запуски обучения"
            self.next_step = "Проверьте подключение к базе данных."
            self.stat_cards = (
                TrainingMetric("Эпоха", "—", "Не удалось загрузить запуски обучения"),
                TrainingMetric("Loss", "—", "Не удалось загрузить запуски обучения"),
                TrainingMetric("Скорость", "—", "Не удалось загрузить запуски обучения"),
                TrainingMetric("Чекпоинты", "—", "Не удалось загрузить запуски обучения"),
            )
            return

        if not runs:
            self.title = "Обучение"
            self.subtitle = "Обучение пока не запускалось"
            self.checkpoints = (
                CheckpointView("Чекпоинты и версии личности", "Чекпоинты и версии личности пока не созданы"),
            )
            return

        current = runs[0]
        self.current_run_id = current.run_id
        self.title = f"Обучение · {current.run_id}"
        self.subtitle = current.subtitle
        self.status = current.status
        self.can_start_run = current.status == "Готов к запуску"
        self.selected_objects = (
            ("Базовая модель", current.base_model),
            ("Профиль", current.profile),
            ("Версия датасета", current.dataset_version),
            ("Режим", current.mode),
        )
        self.stat_cards = (
            TrainingMetric("Эпоха", current.epoch_progress, "статус из реестра запусков"),
            TrainingMetric("Loss", current.loss, "статус из реестра запусков"),
            TrainingMetric("Скорость", current.speed, "статус из реестра запусков"),
            TrainingMetric("Чекпоинты", current.checkpoints_count, "статус из реестра запусков"),
        )
        checkpoints_count = int(current.checkpoints_count) if current.checkpoints_count.isdigit() else 0
        self.checkpoints = tuple(
            CheckpointView(f"chk_{idx + 1:03d}", "из реестра запуска", highlighted=idx == checkpoints_count - 1)
            for idx in range(max(1, checkpoints_count))
        )
        self.logs = (
            f"[реестр] run: {current.run_id}",
            f"[реестр] статус: {current.status}",
            f"[реестр] прогресс: {current.epoch_progress}",
            f"[реестр] loss: {current.loss}",
            f"[реестр] скорость: {current.speed}",
        )
        self.risk_title = "Контроль запуска"
        self.risk_body = "Состояние и метрики читаются из SQLite-реестра запусков обучения."
        self.next_step = "После завершения зафиксируйте snapshot и переходите к тестам."

    def _apply_model_versions_connector(self) -> None:
        if self.model_versions_service is None:
            return

        try:
            versions = self.model_versions_service.list_model_versions()
        except Exception:
            self.versions_status_message = "Не удалось загрузить версии личности"
            self.personality_versions = (
                PersonalityVersionView("Ошибка загрузки", "ошибка", "Не удалось загрузить версии личности"),
            )
            return

        if not versions:
            self.versions_status_message = "Версии личности пока не созданы"
            self.personality_versions = (
                PersonalityVersionView("Ожидание версий", "пусто", "Версии личности пока не созданы"),
            )
            return

        self.versions_status_message = ""
        self.personality_versions = tuple(
            PersonalityVersionView(
                title=item.title,
                status=item.status,
                note=f"{item.base_model} · {item.profile_title} · {item.dataset_title} · {item.training_run_id}\n{item.quality_summary}\n{item.artifact_path}",
            )
            for item in versions
        )

    def _sync_creation_choices(self) -> None:
        if self.training_service is None:
            self.profile_choices = ()
            self.dataset_choices = ()
            return

        try:
            profiles = self.training_service.list_profile_options()
        except Exception:
            profiles = []
        try:
            datasets = self.training_service.list_dataset_options()
        except Exception:
            datasets = []

        self.profile_choices = tuple(
            TrainingProfileChoice(profile_id=item.profile_id, title=item.title)
            for item in profiles
        )
        self.dataset_choices = tuple(
            TrainingDatasetChoice(dataset_id=item.dataset_id, title=item.title, status=item.status)
            for item in datasets
        )

    def refresh(self) -> None:
        self._apply_training_connector()
        self._apply_model_versions_connector()
        self._sync_local_model_info()
        self._sync_creation_choices()

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
    ) -> tuple[bool, str]:
        if self.training_service is None:
            self.creation_message = "Не удалось создать запуск обучения"
            return False, self.creation_message

        try:
            self.training_service.create_training_run(
                title=title,
                profile_id=profile_id,
                dataset_id=dataset_id,
                base_model=base_model,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
            )
        except (TrainingConfigurationError, TrainingValidationError) as exc:
            self.creation_message = str(exc)
            return False, self.creation_message
        except Exception:
            self.creation_message = "Не удалось создать запуск обучения"
            return False, self.creation_message

        self.creation_message = "Запуск обучения создан"
        self.refresh()
        return True, self.creation_message

    def check_local_model(self) -> None:
        self.local_model_status = "Проверка модели…"
        self.local_model_note = "Идёт проверка структуры файлов."
        self.local_inference_status = ""

        if self.local_model_service is None:
            self.local_model_status = "Не удалось проверить модель"
            self.local_model_note = "Сервис локальной модели не подключён."
            return

        try:
            result = self.local_model_service.probe_model_files()
            self.local_model_status = result.status
            self.local_model_note = result.details
        except Exception:
            self.local_model_status = "Не удалось проверить модель"
            self.local_model_note = "Проверьте путь и права доступа к файлам модели."

    def begin_local_inference(self, prompt: str | None = None) -> tuple[bool, str]:
        if self.inference_in_progress:
            return False, self.inference_prompt
        smoke_prompt = (prompt or self.inference_prompt).strip() or "MIA_SENTINEL_FT_TEST_001"
        self.inference_prompt = smoke_prompt
        self.inference_in_progress = True
        self.local_inference_status = "Генерация…"
        self.inference_response = ""
        return True, smoke_prompt

    def run_local_inference_sync(self, prompt: str) -> tuple[str, str]:
        if self.local_model_service is None:
            return "Inference backend не подключён", ""
        try:
            result = self.local_model_service.generate_smoke(prompt)
            return result.status, (result.response or result.message)
        except Exception:
            return "Ошибка генерации", "Не удалось загрузить локальную модель"

    def finish_local_inference(self, status: str, response: str) -> None:
        self.inference_in_progress = False
        self.local_inference_status = status
        self.inference_response = response


    def start_selected_training_run(self) -> tuple[bool, str]:
        if self.training_service is None or not self.current_run_id:
            return False, "Запуск обучения не найден"
        try:
            self.training_service.start_training_run(self.current_run_id)
        except TrainingValidationError as exc:
            self.creation_message = str(exc)
            return False, self.creation_message
        except Exception:
            self.creation_message = "Не удалось запустить обучение"
            return False, self.creation_message
        self.refresh_current_run()
        return True, "Запуск обучения начат"

    def refresh_current_run(self) -> bool:
        if self.training_service is None or not self.current_run_id:
            self.refresh()
            return False
        finished = self.training_service.advance_training_run(self.current_run_id)
        self.refresh()
        if self.current_run_id:
            logs = self.training_service.list_training_run_logs(self.current_run_id)
            if logs:
                self.logs = tuple(logs)
        return finished
