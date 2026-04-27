from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.training.service import TrainingService


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


@dataclass(slots=True)
class TrainingViewModel:
    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
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
        CheckpointView("Ожидание запуска", "Обучение пока не запускалось"),
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

    def __post_init__(self) -> None:
        self._apply_training_connector()
        self._apply_model_versions_connector()

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
            return

        current = runs[0]
        self.title = f"Обучение · {current.run_id}"
        self.subtitle = current.subtitle
        self.status = current.status
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
