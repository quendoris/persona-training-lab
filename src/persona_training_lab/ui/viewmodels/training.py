from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.local_model.service import (
    LocalModelService,
)
from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
    normalize_local_model_status,
)
from persona_training_lab.application.messages import ActionResult
from persona_training_lab.application.model_versions.service import (
    ModelVersionsService,
)
from persona_training_lab.application.training.service import (
    TrainingConfigurationError,
    TrainingService,
    TrainingValidationError,
)
from persona_training_lab.domain.datasets.statuses import (
    DatasetVersionStatus,
)
from persona_training_lab.domain.training.statuses import TrainingRunStatus


_STATUS_KEYS = {
    TrainingRunStatus.CREATED.value: "training.status.created",
    TrainingRunStatus.READY.value: "training.status.ready",
    TrainingRunStatus.RUNNING.value: "training.status.running",
    TrainingRunStatus.FAILED.value: "training.status.failed",
    TrainingRunStatus.COMPLETED.value: "training.status.completed",
}
_DATASET_STATUS_KEYS = {
    DatasetVersionStatus.DRAFT: "datasets.status.unchecked",
    DatasetVersionStatus.IMPORTED: "datasets.status.unchecked",
    DatasetVersionStatus.VALIDATED: "datasets.status.ready",
    DatasetVersionStatus.APPROVED: "datasets.status.approved",
    DatasetVersionStatus.ARCHIVED: "datasets.status.empty",
}
_LOCAL_MODEL_STATUS_KEYS = {
    LocalModelStatus.UNCHECKED: "training.local_model.status.unchecked",
    LocalModelStatus.CHECKING: "training.local_model.status.checking",
    LocalModelStatus.FOUND: "training.local_model.status.found",
    LocalModelStatus.MISSING: "training.local_model.status.missing",
    LocalModelStatus.CHECK_FAILED: "training.local_model.status.check_failed",
    LocalModelStatus.NOT_LOADED: "training.local_model.status.not_loaded",
    LocalModelStatus.RESPONDING: "training.local_model.status.responding",
    LocalModelStatus.INFERENCE_UNAVAILABLE: (
        "training.local_model.status.inference_unavailable"
    ),
    LocalModelStatus.GENERATING: "training.local_model.status.generating",
    LocalModelStatus.GENERATION_FAILED: (
        "training.local_model.status.generation_failed"
    ),
}
_ERROR_CODE_KEYS = {
    "invalid_hyperparameters": "training.message.invalid_hyperparameters",
    "profile_required": "training.message.profile_required",
    "dataset_required": "training.message.dataset_required",
    "model_required": "training.message.model_required",
    "run_not_found": "training.message.run_not_found",
    "already_running": "training.message.already_running",
    "not_ready": "training.message.not_ready",
    "start_failed": "training.message.start_failed",
    "configuration_error": "training.message.create_failed",
    "validation_error": "training.message.start_failed",
}
_ACTION_CODE_KEYS = {
    "backend_unavailable": "training.message.backend_unavailable",
    "model_missing": "training.message.model_missing",
    "resource_busy": "training.message.resource_busy",
    "completed": "training.message.completed",
    "start_failed": "training.message.start_failed",
    "safe_stop": "training.message.safe_stop",
    "run_not_found": "training.message.run_not_found",
    "already_running": "training.message.already_running",
    "not_ready": "training.message.not_ready",
    "started": "training.message.started",
    "created": "training.message.created",
}
_LEGACY_MESSAGE_KEYS = {
    "Training backend не подключён": "training.message.backend_unavailable",
    "Модель не найдена": "training.message.model_missing",
    "Запуск обучения не найден": "training.message.run_not_found",
    "Запуск обучения уже выполняется": "training.message.already_running",
    "Запуск обучения не готов к старту": "training.message.not_ready",
    "Не удалось запустить обучение": "training.message.start_failed",
    "Запуск обучения начат": "training.message.started",
    "Запуск обучения создан": "training.message.created",
}
_VERSION_READY_ALIASES = {
    "готов",
    "готова",
    "ready",
    "available",
}


@dataclass(frozen=True, slots=True)
class TrainingText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


def training_text(key: str, **values: object) -> TrainingText:
    return TrainingText(key, MappingProxyType(dict(values)))


def _base_training_text(value: str | TrainingText) -> str:
    """Render only the historical base-locale compatibility surface lazily."""

    if isinstance(value, str):
        return value
    from persona_training_lab.ui.i18n.text import text as localized_text

    return localized_text(None, value.key, **dict(value.values))


@dataclass(slots=True, frozen=True)
class TrainingMetric:
    title: str
    value: str
    note: str
    title_key: str = ""
    note_key: str = ""


@dataclass(slots=True, frozen=True)
class CheckpointView:
    name: str
    note: str
    highlighted: bool = False
    name_key: str = ""
    note_key: str = ""


@dataclass(slots=True, frozen=True)
class PersonalityVersionView:
    title: str
    status: str
    note: str
    status_code: str = "unknown"
    state: str = "actual"


@dataclass(slots=True, frozen=True)
class TrainingProfileChoice:
    profile_id: str
    title: str


@dataclass(slots=True, frozen=True)
class TrainingDatasetChoice:
    dataset_id: str
    title: str
    status: str
    status_code: DatasetVersionStatus = DatasetVersionStatus.UNKNOWN


@dataclass(slots=True)
class TrainingViewModel:
    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
    local_model_service: LocalModelService | None = None
    title: str = ""
    subtitle: str = ""
    status: str = "ожидание"
    status_code: str = "idle"
    selected_objects: tuple[tuple[str, str], ...] = (
        ("Базовая модель", "—"),
        ("Профиль", "—"),
        ("Версия датасета", "—"),
        ("Режим", "—"),
    )
    stat_cards: tuple[TrainingMetric, ...] = (
        TrainingMetric(
            "Эпоха",
            "—",
            "Обучение пока не запускалось",
            "training.metric.epoch",
            "training.metric.note.idle",
        ),
        TrainingMetric(
            "Loss",
            "—",
            "Обучение пока не запускалось",
            "training.metric.loss",
            "training.metric.note.idle",
        ),
        TrainingMetric(
            "Скорость",
            "—",
            "Обучение пока не запускалось",
            "training.metric.speed",
            "training.metric.note.idle",
        ),
        TrainingMetric(
            "Чекпоинты",
            "00",
            "Обучение пока не запускалось",
            "training.metric.checkpoints",
            "training.metric.note.idle",
        ),
    )
    checkpoints: tuple[CheckpointView, ...] = (
        CheckpointView(
            "Чекпоинты и версии личности",
            "Чекпоинты и версии личности пока не созданы",
            name_key="training.checkpoint.empty.title",
            note_key="training.checkpoint.empty.note",
        ),
    )
    personality_versions: tuple[PersonalityVersionView, ...] = (
        PersonalityVersionView(
            "Ожидание версий",
            "пусто",
            "Версии личности пока не созданы",
            status_code="empty",
            state="empty",
        ),
    )
    versions_status_message: str = "Версии личности пока не созданы"
    logs: tuple[str, ...] = ("[—] Обучение пока не запускалось",)
    monitor_rows: tuple[tuple[str, int, str], ...] = (
        ("Нагрузка GPU", 0, "нет активного запуска"),
        ("Видеопамять", 0, "нет активного запуска"),
        ("Память RAM", 0, "нет активного запуска"),
    )
    risk_title: str = "Статус"
    risk_body: str = "Обучение пока не запускалось"
    next_step: str = (
        "Выберите профиль и датасет, затем запустите обучение."
    )
    local_model_name: str = "Qwen3.5-0.8B"
    local_model_path: str = "models/qwen3.5-0.8b"
    local_model_status: str = "Модель не проверялась"
    local_model_status_code: LocalModelStatus = LocalModelStatus.UNCHECKED
    local_model_note: str = (
        "Проверка файлов модели выполняется по запросу."
    )
    local_inference_status: str = ""
    local_inference_status_code: LocalModelStatus = LocalModelStatus.UNKNOWN
    inference_prompt: str = "MIA_SENTINEL_FT_TEST_001"
    inference_response: str = ""
    inference_in_progress: bool = False
    artifact_path: str = ""
    creation_message: str = ""
    profile_choices: tuple[TrainingProfileChoice, ...] = ()
    dataset_choices: tuple[TrainingDatasetChoice, ...] = ()
    current_run_id: str = ""
    can_start_run: bool = False
    training_in_progress: bool = False
    progress_value: int = 0
    progress_note: str = "ожидание метрики"
    _title_model: str | TrainingText = field(
        default_factory=lambda: training_text("training.header.title")
    )
    _subtitle_model: str | TrainingText = field(
        default_factory=lambda: training_text(
            "training.header.subtitle.idle"
        )
    )
    _status_model: str | TrainingText = field(
        default_factory=lambda: training_text("training.status.idle")
    )
    _progress_model: str | TrainingText = field(
        default_factory=lambda: training_text("training.progress.waiting")
    )
    _log_models: tuple[str | TrainingText, ...] = field(
        default_factory=lambda: (training_text("training.log.idle"),)
    )
    _creation_message_model: str | TrainingText | None = None
    _local_model_note_model: str | TrainingText = field(
        default_factory=lambda: training_text(
            "training.local_model.note.unchecked"
        )
    )
    _local_inference_status_model: str | TrainingText | None = None

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

    def _latest_run(self):
        if self.training_service is None:
            return None
        runs = self.training_service.list_training_runs()
        return runs[0] if runs else None

    def _set_idle_state(self) -> None:
        self._title_model = training_text("training.header.title")
        self._subtitle_model = training_text(
            "training.header.subtitle.idle"
        )
        self.title = _base_training_text(self._title_model)
        self.subtitle = _base_training_text(self._subtitle_model)
        self.status = "ожидание"
        self.status_code = "idle"
        self.current_run_id = ""
        self.can_start_run = False
        self.training_in_progress = False
        self.artifact_path = ""
        self.progress_value = 0
        self.progress_note = "ожидание метрики"
        self._status_model = training_text("training.status.idle")
        self._progress_model = training_text("training.progress.waiting")
        self.logs = ("[—] Обучение пока не запускалось",)
        self._log_models = (training_text("training.log.idle"),)
        self.stat_cards = self._metric_cards(
            note="Обучение пока не запускалось",
            note_key="training.metric.note.idle",
            checkpoint_value="00",
        )
        self.checkpoints = (
            CheckpointView(
                "Чекпоинты и версии личности",
                "Чекпоинты и версии личности пока не созданы",
                name_key="training.checkpoint.empty.title",
                note_key="training.checkpoint.empty.note",
            ),
        )

    def _set_load_error_state(self) -> None:
        self._title_model = training_text("training.header.title")
        self._subtitle_model = training_text(
            "training.header.subtitle.load_failed"
        )
        self.title = _base_training_text(self._title_model)
        self.subtitle = _base_training_text(self._subtitle_model)
        self.status = "ошибка"
        self.status_code = TrainingRunStatus.FAILED.value
        self.can_start_run = False
        self.training_in_progress = False
        self._status_model = training_text("training.status.failed")
        self.logs = ("[—] Не удалось загрузить запуски обучения",)
        self._log_models = (training_text("training.log.load_failed"),)
        self.risk_title = "Статус"
        self.risk_body = "Не удалось загрузить запуски обучения"
        self.next_step = "Проверьте подключение к базе данных."
        self.stat_cards = self._metric_cards(
            note="Не удалось загрузить запуски обучения",
            note_key="training.metric.note.load_failed",
            checkpoint_value="—",
        )

    @staticmethod
    def _metric_cards(
        *,
        note: str,
        note_key: str,
        checkpoint_value: str,
    ) -> tuple[TrainingMetric, ...]:
        return (
            TrainingMetric(
                "Эпоха",
                "—",
                note,
                "training.metric.epoch",
                note_key,
            ),
            TrainingMetric(
                "Loss",
                "—",
                note,
                "training.metric.loss",
                note_key,
            ),
            TrainingMetric(
                "Скорость",
                "—",
                note,
                "training.metric.speed",
                note_key,
            ),
            TrainingMetric(
                "Чекпоинты",
                checkpoint_value,
                note,
                "training.metric.checkpoints",
                note_key,
            ),
        )

    def _apply_training_connector(self) -> None:
        if self.training_service is None:
            self._set_idle_state()
            return

        try:
            runs = self.training_service.list_training_runs()
        except Exception:
            self._set_load_error_state()
            return

        if not runs:
            self._set_idle_state()
            return

        current = runs[0]
        self.current_run_id = current.run_id
        self._title_model = training_text(
            "training.header.title.run",
            run_id=current.run_id,
        )
        self._subtitle_model = current.subtitle
        self.title = _base_training_text(self._title_model)
        self.subtitle = _base_training_text(self._subtitle_model)
        self.status = current.status
        self.status_code = current.status_code.value
        self.can_start_run = (
            current.status_code is TrainingRunStatus.READY
        )
        self.training_in_progress = (
            current.status_code is TrainingRunStatus.RUNNING
        )
        self.artifact_path = current.artifact_path
        self._status_model = self._status_text(
            current.status_code.value,
            current.status,
        )
        try:
            self.progress_value = max(
                0,
                min(100, int(float(current.progress) * 100)),
            )
        except Exception:
            self.progress_value = 0
        if current.progress:
            self.progress_note = (
                "Прогресс обучения · "
                f"{self.progress_value}% | эпоха {current.epoch_progress}"
            )
            self._progress_model = training_text(
                "training.progress.value",
                percent=self.progress_value,
                epoch=current.epoch_progress,
            )
        else:
            self.progress_note = "Прогресс обучения · ожидание метрики"
            self._progress_model = training_text(
                "training.progress.waiting"
            )
        self.selected_objects = (
            ("Базовая модель", current.base_model),
            ("Профиль", current.profile),
            ("Версия датасета", current.dataset_version),
            ("Режим", current.mode),
        )
        self.stat_cards = (
            TrainingMetric(
                "Эпоха",
                current.epoch_progress,
                "статус из реестра запусков",
                "training.metric.epoch",
                "training.metric.note.registry",
            ),
            TrainingMetric(
                "Loss",
                current.loss,
                "статус из реестра запусков",
                "training.metric.loss",
                "training.metric.note.registry",
            ),
            TrainingMetric(
                "Скорость",
                current.speed,
                "статус из реестра запусков",
                "training.metric.speed",
                "training.metric.note.registry",
            ),
            TrainingMetric(
                "Чекпоинты",
                current.checkpoints_count,
                "статус из реестра запусков",
                "training.metric.checkpoints",
                "training.metric.note.registry",
            ),
        )
        checkpoints_count = (
            int(current.checkpoints_count)
            if current.checkpoints_count.isdigit()
            else 0
        )
        checkpoint_rows = [
            CheckpointView(
                f"chk_{idx + 1:03d}",
                "из реестра запуска",
                highlighted=idx == checkpoints_count - 1,
                note_key="training.checkpoint.registry_note",
            )
            for idx in range(max(0, checkpoints_count))
        ]
        if current.artifact_path:
            checkpoint_rows.append(
                CheckpointView(
                    "model artifact",
                    current.artifact_path,
                    highlighted=(
                        current.status_code
                        is TrainingRunStatus.COMPLETED
                    ),
                    name_key="training.checkpoint.artifact",
                )
            )
        self.checkpoints = tuple(checkpoint_rows) or (
            CheckpointView(
                "Чекпоинты и версии личности",
                "Чекпоинты и версии личности пока не созданы",
                name_key="training.checkpoint.empty.title",
                note_key="training.checkpoint.empty.note",
            ),
        )
        repo_logs = self.training_service.list_training_run_logs(
            current.run_id
        )
        self.logs = tuple(repo_logs) if repo_logs else (
            f"[реестр] run: {current.run_id}",
            f"[реестр] статус: {current.status}",
            f"[реестр] прогресс: {current.epoch_progress}",
            f"[реестр] loss: {current.loss}",
            f"[реестр] скорость: {current.speed}",
        )
        self._log_models = tuple(self.logs)
        self.risk_title = "Контроль запуска"
        self.risk_body = (
            "Состояние и метрики читаются из SQLite-реестра "
            "запусков обучения."
        )
        self.next_step = (
            "После завершения зафиксируйте snapshot и переходите к "
            "тестам."
        )

    def _apply_model_versions_connector(self) -> None:
        if self.model_versions_service is None:
            return

        try:
            versions = self.model_versions_service.list_model_versions()
        except Exception:
            self.versions_status_message = (
                "Не удалось загрузить версии личности"
            )
            self.personality_versions = (
                PersonalityVersionView(
                    "Ошибка загрузки",
                    "ошибка",
                    "Не удалось загрузить версии личности",
                    status_code="error",
                    state="error",
                ),
            )
            return
        if not versions:
            self.versions_status_message = (
                "Версии личности пока не созданы"
            )
            self.personality_versions = (
                PersonalityVersionView(
                    "Ожидание версий",
                    "пусто",
                    "Версии личности пока не созданы",
                    status_code="empty",
                    state="empty",
                ),
            )
            return
        self.versions_status_message = ""
        self.personality_versions = tuple(
            PersonalityVersionView(
                title=item.title,
                status=item.status,
                note=(
                    f"{item.base_model} · {item.profile_title} · "
                    f"{item.dataset_title} · {item.training_run_id}\n"
                    f"{item.quality_summary}\n{item.artifact_path}"
                ),
                status_code=(
                    "ready"
                    if item.status.strip().casefold()
                    in _VERSION_READY_ALIASES
                    else "unknown"
                ),
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
            TrainingProfileChoice(
                profile_id=item.profile_id,
                title=item.title,
            )
            for item in profiles
        )
        self.dataset_choices = tuple(
            TrainingDatasetChoice(
                dataset_id=item.dataset_id,
                title=item.title,
                status=item.status,
                status_code=item.status_code,
            )
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
            self.creation_message = "create_failed"
            self._creation_message_model = training_text(
                "training.message.create_failed"
            )
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
            self.creation_message = exc.code
            self._creation_message_model = training_text(
                _ERROR_CODE_KEYS.get(
                    exc.code,
                    "training.message.create_failed",
                )
            )
            return False, self.creation_message
        except Exception:
            self.creation_message = "create_failed"
            self._creation_message_model = training_text(
                "training.message.create_failed"
            )
            return False, self.creation_message

        self.creation_message = "created"
        self._creation_message_model = training_text(
            "training.message.created"
        )
        self.refresh()
        return True, self.creation_message

    def check_local_model(self) -> None:
        self.local_model_status = "Проверка модели…"
        self.local_model_status_code = LocalModelStatus.CHECKING
        self.local_model_note = "Идёт проверка структуры файлов."
        self._local_model_note_model = training_text(
            "training.local_model.note.checking"
        )
        self.local_inference_status = ""
        self.local_inference_status_code = LocalModelStatus.UNKNOWN
        self._local_inference_status_model = None

        if self.local_model_service is None:
            self.local_model_status = "Не удалось проверить модель"
            self.local_model_status_code = LocalModelStatus.CHECK_FAILED
            self.local_model_note = (
                "Сервис локальной модели не подключён."
            )
            self._local_model_note_model = training_text(
                "training.local_model.note.service_unavailable"
            )
            return
        try:
            result = self.local_model_service.probe_model_files()
            self.local_model_status = result.status
            self.local_model_status_code = normalize_local_model_status(
                result.status
            )
            self.local_model_note = result.details
            self._local_model_note_model = result.details
        except Exception:
            self.local_model_status = "Не удалось проверить модель"
            self.local_model_status_code = LocalModelStatus.CHECK_FAILED
            self.local_model_note = (
                "Проверьте путь и права доступа к файлам модели."
            )
            self._local_model_note_model = training_text(
                "training.local_model.note.check_failed"
            )

    def begin_local_inference(
        self,
        prompt: str | None = None,
    ) -> tuple[bool, str]:
        if self.inference_in_progress:
            return False, self.inference_prompt
        smoke_prompt = (
            (prompt or self.inference_prompt).strip()
            or "MIA_SENTINEL_FT_TEST_001"
        )
        self.inference_prompt = smoke_prompt
        self.inference_in_progress = True
        self.local_inference_status = "Генерация…"
        self.local_inference_status_code = LocalModelStatus.GENERATING
        self._local_inference_status_model = training_text(
            "training.inference.status.generating"
        )
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
        self.local_inference_status_code = normalize_local_model_status(
            status
        )
        self._local_inference_status_model = self._local_status_text(
            self.local_inference_status_code,
            status,
        )
        self.inference_response = response

    def _publish_latest_completed_run(self) -> None:
        if (
            self.training_service is None
            or self.model_versions_service is None
        ):
            return
        try:
            current = self._latest_run()
        except Exception:
            return
        if (
            current is None
            or current.status_code is not TrainingRunStatus.COMPLETED
            or not current.artifact_path
        ):
            return
        try:
            created = self.model_versions_service.create_from_training_run(
                training_run_id=current.run_id,
                base_model=current.base_model,
                profile_title=current.profile,
                dataset_title=current.dataset_version,
                artifact_path=current.artifact_path,
                quality_summary=(
                    "Full fine-tune завершён · "
                    f"loss {current.loss} · checkpoints "
                    f"{current.checkpoints_count}"
                ),
            )
            if created is not None:
                logger = getattr(self.training_service, "_log", None)
                if logger is not None:
                    logger(
                        current.run_id,
                        "Model version registered: "
                        f"{created.version_id}",
                    )
        except Exception:
            return

    def start_selected_training_run(self) -> tuple[bool, str]:
        if self.training_service is None or not self.current_run_id:
            self.creation_message = "run_not_found"
            self._creation_message_model = training_text(
                "training.message.run_not_found"
            )
            return False, self.creation_message
        try:
            result = self.training_service.start_real_or_skeleton_run(
                self.current_run_id
            )
        except TrainingValidationError as exc:
            self.creation_message = exc.code
            self._creation_message_model = training_text(
                _ERROR_CODE_KEYS.get(
                    exc.code,
                    "training.message.start_failed",
                )
            )
            return False, self.creation_message
        except Exception:
            self.creation_message = "start_failed"
            self._creation_message_model = training_text(
                "training.message.start_failed"
            )
            return False, self.creation_message

        self.refresh()
        if self.current_run_id:
            logs = self.training_service.list_training_run_logs(
                self.current_run_id
            )
            if logs:
                self.logs = tuple(logs)
                self._log_models = tuple(logs)

        if self.status_code == TrainingRunStatus.COMPLETED.value:
            self._publish_latest_completed_run()
            self._apply_model_versions_connector()

        self.creation_message = result.code
        self._creation_message_model = self._action_result_model(result)
        return result.ok, result.code

    def begin_training_run(self) -> bool:
        if self.training_in_progress or not self.can_start_run:
            return False
        self.training_in_progress = True
        self.can_start_run = False
        self.status = "Выполняется"
        self.status_code = TrainingRunStatus.RUNNING.value
        self._status_model = training_text("training.status.running")
        self.creation_message = "started"
        self._creation_message_model = training_text(
            "training.message.started"
        )
        return True

    def finish_training_run(self, success: bool, message: str) -> None:
        self.training_in_progress = False
        self.creation_message = message
        self._creation_message_model = (
            self._message_from_legacy(message)
            if not success
            else training_text("training.message.started")
        )
        self.refresh()
        if self.current_run_id and self.training_service is not None:
            logs = self.training_service.list_training_run_logs(
                self.current_run_id
            )
            if logs:
                self.logs = tuple(logs)
                self._log_models = tuple(logs)

    def refresh_current_run(self) -> bool:
        if self.training_service is None or not self.current_run_id:
            self.refresh()
            return False
        finished = self.training_service.advance_training_run(
            self.current_run_id
        )
        self.refresh()
        if self.current_run_id:
            logs = self.training_service.list_training_run_logs(
                self.current_run_id
            )
            if logs:
                self.logs = tuple(logs)
                self._log_models = tuple(logs)
        return finished

    def poll_current_run(self) -> None:
        self.refresh()
        if self.current_run_id and self.training_service is not None:
            logs = self.training_service.list_training_run_logs(
                self.current_run_id
            )
            if logs:
                self.logs = tuple(logs)
                self._log_models = tuple(logs)

    def header_title_model(self) -> str | TrainingText:
        return self._title_model

    def header_subtitle_model(self) -> str | TrainingText:
        return self._subtitle_model

    def status_model(self) -> str | TrainingText:
        return self._status_model

    def progress_model(self) -> str | TrainingText:
        return self._progress_model

    def log_models(self) -> tuple[str | TrainingText, ...]:
        return self._log_models

    def current_message(self) -> str | TrainingText | None:
        return self._creation_message_model

    def local_model_status_model(self) -> str | TrainingText:
        return self._local_status_text(
            self.local_model_status_code,
            self.local_model_status,
        )

    def local_model_note_model(self) -> str | TrainingText:
        return self._local_model_note_model

    def local_inference_status_model(
        self,
    ) -> str | TrainingText | None:
        return self._local_inference_status_model

    @staticmethod
    def metric_title_model(
        metric: TrainingMetric,
    ) -> str | TrainingText:
        return training_text(metric.title_key) if metric.title_key else metric.title

    @staticmethod
    def metric_note_model(
        metric: TrainingMetric,
    ) -> str | TrainingText:
        return training_text(metric.note_key) if metric.note_key else metric.note

    @staticmethod
    def checkpoint_name_model(
        checkpoint: CheckpointView,
    ) -> str | TrainingText:
        return (
            training_text(checkpoint.name_key)
            if checkpoint.name_key
            else checkpoint.name
        )

    @staticmethod
    def checkpoint_note_model(
        checkpoint: CheckpointView,
    ) -> str | TrainingText:
        return (
            training_text(checkpoint.note_key)
            if checkpoint.note_key
            else checkpoint.note
        )

    @staticmethod
    def version_title_model(
        version: PersonalityVersionView,
    ) -> str | TrainingText:
        if version.state == "empty":
            return training_text("training.version.empty.title")
        if version.state == "error":
            return training_text("training.version.error.title")
        return training_text(
            "training.version.title",
            title=version.title,
        )

    @staticmethod
    def version_status_model(
        version: PersonalityVersionView,
    ) -> str | TrainingText:
        if version.state == "empty":
            return training_text("training.version.empty.status")
        if version.state == "error":
            return training_text("training.version.error.status")
        if version.status_code == "ready":
            return training_text("training.version.ready")
        return training_text(
            "training.raw",
            value=version.status,
        )

    @staticmethod
    def version_note_model(
        version: PersonalityVersionView,
    ) -> str | TrainingText:
        if version.state == "empty":
            return training_text("training.version.empty.note")
        if version.state == "error":
            return training_text("training.version.error.note")
        return version.note

    @staticmethod
    def dataset_status_model(
        dataset: TrainingDatasetChoice,
    ) -> str | TrainingText:
        key = _DATASET_STATUS_KEYS.get(dataset.status_code)
        if key is not None:
            return training_text(key)
        return training_text("training.raw", value=dataset.status)

    @staticmethod
    def selected_object_models(
        selected_objects: tuple[tuple[str, str], ...],
    ) -> tuple[tuple[TrainingText, str], ...]:
        keys = (
            "training.selected.base_model",
            "training.selected.profile",
            "training.selected.dataset",
            "training.selected.mode",
        )
        return tuple(
            (training_text(key), value)
            for key, (_legacy, value) in zip(
                keys,
                selected_objects,
                strict=False,
            )
        )

    @staticmethod
    def _status_text(
        status_code: str,
        raw_status: str,
    ) -> TrainingText:
        key = _STATUS_KEYS.get(status_code)
        if key is not None:
            return training_text(key)
        return training_text(
            "training.status.unknown",
            status=raw_status,
        )

    @staticmethod
    def _local_status_text(
        status_code: LocalModelStatus,
        raw_status: str,
    ) -> TrainingText:
        key = _LOCAL_MODEL_STATUS_KEYS.get(status_code)
        if key is not None:
            return training_text(key)
        return training_text(
            "training.local_model.status.unknown",
            status=raw_status,
        )

    @staticmethod
    def _action_result_model(result: ActionResult) -> TrainingText:
        key = _ACTION_CODE_KEYS.get(
            result.code,
            "training.message.start_failed",
        )
        return training_text(key, **dict(result.values))

    @staticmethod
    def _message_from_legacy(message: str) -> TrainingText:
        key = _LEGACY_MESSAGE_KEYS.get(message)
        if key is not None:
            return training_text(key)
        if message.startswith("Запуск временно недоступен:"):
            return training_text("training.message.resource_busy")
        if message.startswith("Обучение остановлено безопасно"):
            return training_text("training.message.safe_stop")
        return training_text(
            "training.message.raw",
            message=message,
        )