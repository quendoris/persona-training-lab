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
from persona_training_lab.domain.models.statuses import ModelVersionStatus
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
_MODEL_VERSION_STATUS_KEYS = {
    ModelVersionStatus.DRAFT: "training.version.status.draft",
    ModelVersionStatus.READY: "training.version.ready",
    ModelVersionStatus.ARCHIVED: "training.version.status.archived",
    ModelVersionStatus.FAILED: "training.version.status.failed",
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
_SELECTED_OBJECT_KEYS = (
    "training.selected.base_model",
    "training.selected.profile",
    "training.selected.dataset",
    "training.selected.mode",
)


@dataclass(frozen=True, slots=True)
class TrainingText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


def training_text(key: str, **values: object) -> TrainingText:
    return TrainingText(key, MappingProxyType(dict(values)))


TrainingTextValue = str | TrainingText


def _base_training_text(value: TrainingTextValue) -> str:
    """Render the historical base-locale compatibility surface lazily."""

    if isinstance(value, str):
        return value
    from persona_training_lab.ui.i18n.text import text as localized_text

    rendered_values = {
        key: (
            _base_training_text(item)
            if isinstance(item, TrainingText)
            else item
        )
        for key, item in value.values.items()
    }
    return localized_text(None, value.key, **rendered_values)


@dataclass(slots=True, frozen=True)
class TrainingMetric:
    title: str
    value: str
    note: str
    title_key: str = ""
    note_key: str = ""
    title_model: TrainingTextValue | None = None
    note_model: TrainingTextValue | None = None


def _training_metric(
    title: TrainingTextValue,
    value: str,
    note: TrainingTextValue,
) -> TrainingMetric:
    return TrainingMetric(
        title=_base_training_text(title),
        value=value,
        note=_base_training_text(note),
        title_key=title.key if isinstance(title, TrainingText) else "",
        note_key=note.key if isinstance(note, TrainingText) else "",
        title_model=title,
        note_model=note,
    )


@dataclass(slots=True, frozen=True)
class CheckpointView:
    name: str
    note: str
    highlighted: bool = False
    name_key: str = ""
    note_key: str = ""
    name_model: TrainingTextValue | None = None
    note_model: TrainingTextValue | None = None


def _checkpoint_view(
    name: TrainingTextValue,
    note: TrainingTextValue,
    *,
    highlighted: bool = False,
) -> CheckpointView:
    return CheckpointView(
        name=_base_training_text(name),
        note=_base_training_text(note),
        highlighted=highlighted,
        name_key=name.key if isinstance(name, TrainingText) else "",
        note_key=note.key if isinstance(note, TrainingText) else "",
        name_model=name,
        note_model=note,
    )


@dataclass(slots=True, frozen=True)
class PersonalityVersionView:
    title: str
    status: str
    note: str
    status_code: str = "unknown"
    state: str = "actual"
    title_model: TrainingTextValue | None = None
    status_model: TrainingTextValue | None = None
    note_model: TrainingTextValue | None = None


def _personality_version(
    title: TrainingTextValue,
    status: TrainingTextValue,
    note: TrainingTextValue,
    *,
    status_code: str = "unknown",
    state: str = "actual",
    raw_title: str | None = None,
    raw_status: str | None = None,
    raw_note: str | None = None,
) -> PersonalityVersionView:
    return PersonalityVersionView(
        title=raw_title if raw_title is not None else _base_training_text(title),
        status=(
            raw_status
            if raw_status is not None
            else _base_training_text(status)
        ),
        note=raw_note if raw_note is not None else _base_training_text(note),
        status_code=status_code,
        state=state,
        title_model=title,
        status_model=status,
        note_model=note,
    )


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


def _selected_models(
    values: tuple[str, str, str, str],
) -> tuple[tuple[TrainingText, str], ...]:
    return tuple(
        (training_text(key), value)
        for key, value in zip(_SELECTED_OBJECT_KEYS, values, strict=True)
    )


def _compat_selected_objects(
    models: tuple[tuple[TrainingText, str], ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (_base_training_text(label), value)
        for label, value in models
    )


def _empty_selected_models() -> tuple[tuple[TrainingText, str], ...]:
    return _selected_models(("—", "—", "—", "—"))


def _idle_metrics() -> tuple[TrainingMetric, ...]:
    note = training_text("training.metric.note.idle")
    return (
        _training_metric(training_text("training.metric.epoch"), "—", note),
        _training_metric(training_text("training.metric.loss"), "—", note),
        _training_metric(training_text("training.metric.speed"), "—", note),
        _training_metric(
            training_text("training.metric.checkpoints"),
            "00",
            note,
        ),
    )


def _empty_checkpoints() -> tuple[CheckpointView, ...]:
    return (
        _checkpoint_view(
            training_text("training.checkpoint.empty.title"),
            training_text("training.checkpoint.empty.note"),
        ),
    )


def _empty_versions() -> tuple[PersonalityVersionView, ...]:
    return (
        _personality_version(
            training_text("training.version.empty.title"),
            training_text("training.version.empty.status"),
            training_text("training.version.empty.note"),
            status_code="empty",
            state="empty",
        ),
    )


def _idle_logs() -> tuple[TrainingTextValue, ...]:
    return (training_text("training.log.idle"),)


def _idle_monitor_models() -> tuple[tuple[TrainingText, int, TrainingText], ...]:
    inactive = training_text("training.monitor.inactive")
    return (
        (training_text("training.monitor.gpu"), 0, inactive),
        (training_text("training.monitor.vram"), 0, inactive),
        (training_text("training.monitor.ram"), 0, inactive),
    )


def _compat_monitor_rows(
    models: tuple[tuple[TrainingText, int, TrainingTextValue], ...],
) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (
            _base_training_text(label),
            value,
            _base_training_text(note),
        )
        for label, value, note in models
    )


@dataclass(slots=True)
class TrainingViewModel:
    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
    local_model_service: LocalModelService | None = None
    title: str = ""
    subtitle: str = ""
    status: str = field(
        default_factory=lambda: _base_training_text(
            training_text("training.status.idle")
        )
    )
    status_code: str = "idle"
    selected_objects: tuple[tuple[str, str], ...] = field(
        default_factory=lambda: _compat_selected_objects(
            _empty_selected_models()
        )
    )
    stat_cards: tuple[TrainingMetric, ...] = field(
        default_factory=_idle_metrics
    )
    checkpoints: tuple[CheckpointView, ...] = field(
        default_factory=_empty_checkpoints
    )
    personality_versions: tuple[PersonalityVersionView, ...] = field(
        default_factory=_empty_versions
    )
    versions_status_message: str = field(
        default_factory=lambda: _base_training_text(
            training_text("training.version.empty.note")
        )
    )
    logs: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            _base_training_text(item) for item in _idle_logs()
        )
    )
    monitor_rows: tuple[tuple[str, int, str], ...] = field(
        default_factory=lambda: _compat_monitor_rows(
            _idle_monitor_models()
        )
    )
    risk_title: str = field(
        default_factory=lambda: _base_training_text(
            training_text("training.risk.title.status")
        )
    )
    risk_body: str = field(
        default_factory=lambda: _base_training_text(
            training_text("training.risk.body.idle")
        )
    )
    next_step: str = field(
        default_factory=lambda: _base_training_text(
            training_text("training.next.idle")
        )
    )
    local_model_name: str = "Qwen3.5-0.8B"
    local_model_path: str = "models/qwen3.5-0.8b"
    local_model_status: str = field(
        default_factory=lambda: _base_training_text(
            training_text("training.local_model.status.unchecked")
        )
    )
    local_model_status_code: LocalModelStatus = LocalModelStatus.UNCHECKED
    local_model_note: str = field(
        default_factory=lambda: _base_training_text(
            training_text("training.local_model.note.unchecked")
        )
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
    progress_note: str = field(
        default_factory=lambda: _base_training_text(
            training_text("training.progress.waiting")
        )
    )
    _title_model: TrainingTextValue = field(
        default_factory=lambda: training_text("training.header.title")
    )
    _subtitle_model: TrainingTextValue = field(
        default_factory=lambda: training_text(
            "training.header.subtitle.idle"
        )
    )
    _status_model: TrainingTextValue = field(
        default_factory=lambda: training_text("training.status.idle")
    )
    _selected_object_models: tuple[tuple[TrainingText, str], ...] = field(
        default_factory=_empty_selected_models
    )
    _progress_model: TrainingTextValue = field(
        default_factory=lambda: training_text("training.progress.waiting")
    )
    _log_models: tuple[TrainingTextValue, ...] = field(
        default_factory=_idle_logs
    )
    _monitor_models: tuple[
        tuple[TrainingText, int, TrainingTextValue], ...
    ] = field(default_factory=_idle_monitor_models)
    _risk_title_model: TrainingTextValue = field(
        default_factory=lambda: training_text("training.risk.title.status")
    )
    _risk_body_model: TrainingTextValue = field(
        default_factory=lambda: training_text("training.risk.body.idle")
    )
    _next_step_model: TrainingTextValue = field(
        default_factory=lambda: training_text("training.next.idle")
    )
    _versions_status_model: TrainingTextValue | None = field(
        default_factory=lambda: training_text("training.version.empty.note")
    )
    _creation_message_model: TrainingTextValue | None = None
    _local_model_status_model: TrainingTextValue = field(
        default_factory=lambda: training_text(
            "training.local_model.status.unchecked"
        )
    )
    _local_model_note_model: TrainingTextValue = field(
        default_factory=lambda: training_text(
            "training.local_model.note.unchecked"
        )
    )
    _local_inference_status_model: TrainingTextValue | None = None

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

    def _set_header_models(
        self,
        title: TrainingTextValue,
        subtitle: TrainingTextValue,
    ) -> None:
        self._title_model = title
        self._subtitle_model = subtitle
        self.title = _base_training_text(title)
        self.subtitle = _base_training_text(subtitle)

    def _set_status_model(
        self,
        model: TrainingTextValue,
        *,
        raw_status: str | None = None,
    ) -> None:
        self._status_model = model
        self.status = (
            raw_status if raw_status is not None else _base_training_text(model)
        )

    def _set_progress_model(self, model: TrainingTextValue) -> None:
        self._progress_model = model
        self.progress_note = _base_training_text(model)

    def _set_selected_values(
        self,
        values: tuple[str, str, str, str],
    ) -> None:
        self._selected_object_models = _selected_models(values)
        self.selected_objects = _compat_selected_objects(
            self._selected_object_models
        )

    def _set_log_models(
        self,
        models: tuple[TrainingTextValue, ...],
    ) -> None:
        self._log_models = models
        self.logs = tuple(_base_training_text(item) for item in models)

    def _set_monitor_models(
        self,
        models: tuple[tuple[TrainingText, int, TrainingTextValue], ...],
    ) -> None:
        self._monitor_models = models
        self.monitor_rows = _compat_monitor_rows(models)

    def _set_risk_models(
        self,
        title: TrainingTextValue,
        body: TrainingTextValue,
        next_step: TrainingTextValue,
    ) -> None:
        self._risk_title_model = title
        self._risk_body_model = body
        self._next_step_model = next_step
        self.risk_title = _base_training_text(title)
        self.risk_body = _base_training_text(body)
        self.next_step = _base_training_text(next_step)

    def _set_versions_status_model(
        self,
        model: TrainingTextValue | None,
    ) -> None:
        self._versions_status_model = model
        self.versions_status_message = (
            _base_training_text(model) if model is not None else ""
        )

    def _set_local_model_state(
        self,
        status_code: LocalModelStatus,
        status_model: TrainingTextValue,
        note_model: TrainingTextValue,
        *,
        raw_status: str | None = None,
        raw_note: str | None = None,
    ) -> None:
        self.local_model_status_code = status_code
        self._local_model_status_model = status_model
        self._local_model_note_model = note_model
        self.local_model_status = (
            raw_status
            if raw_status is not None
            else _base_training_text(status_model)
        )
        self.local_model_note = (
            raw_note if raw_note is not None else _base_training_text(note_model)
        )

    def _set_idle_state(self) -> None:
        self._set_header_models(
            training_text("training.header.title"),
            training_text("training.header.subtitle.idle"),
        )
        self._set_status_model(training_text("training.status.idle"))
        self.status_code = "idle"
        self.current_run_id = ""
        self.can_start_run = False
        self.training_in_progress = False
        self.artifact_path = ""
        self.progress_value = 0
        self._set_progress_model(training_text("training.progress.waiting"))
        self._set_selected_values(("—", "—", "—", "—"))
        self._set_log_models(_idle_logs())
        self.stat_cards = _idle_metrics()
        self.checkpoints = _empty_checkpoints()
        self._set_monitor_models(_idle_monitor_models())
        self._set_risk_models(
            training_text("training.risk.title.status"),
            training_text("training.risk.body.idle"),
            training_text("training.next.idle"),
        )

    def _set_load_error_state(self) -> None:
        self._set_header_models(
            training_text("training.header.title"),
            training_text("training.header.subtitle.load_failed"),
        )
        self._set_status_model(training_text("training.status.failed"))
        self.status_code = TrainingRunStatus.FAILED.value
        self.can_start_run = False
        self.training_in_progress = False
        self.progress_value = 0
        self._set_progress_model(training_text("training.progress.waiting"))
        self._set_selected_values(("—", "—", "—", "—"))
        self._set_log_models((training_text("training.log.load_failed"),))
        self._set_risk_models(
            training_text("training.risk.title.status"),
            training_text("training.risk.body.load_failed"),
            training_text("training.next.load_failed"),
        )
        self.stat_cards = self._metric_cards(
            note=training_text("training.metric.note.load_failed"),
            checkpoint_value="—",
        )

    @staticmethod
    def _metric_cards(
        *,
        note: TrainingTextValue,
        checkpoint_value: str,
    ) -> tuple[TrainingMetric, ...]:
        return (
            _training_metric(
                training_text("training.metric.epoch"),
                "—",
                note,
            ),
            _training_metric(
                training_text("training.metric.loss"),
                "—",
                note,
            ),
            _training_metric(
                training_text("training.metric.speed"),
                "—",
                note,
            ),
            _training_metric(
                training_text("training.metric.checkpoints"),
                checkpoint_value,
                note,
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
        self._set_header_models(
            training_text(
                "training.header.title.run",
                run_id=current.run_id,
            ),
            current.subtitle,
        )
        self.status_code = current.status_code.value
        self._set_status_model(
            self._status_text(current.status_code.value, current.status),
            raw_status=current.status,
        )
        self.can_start_run = current.status_code is TrainingRunStatus.READY
        self.training_in_progress = (
            current.status_code is TrainingRunStatus.RUNNING
        )
        self.artifact_path = current.artifact_path
        try:
            self.progress_value = max(
                0,
                min(100, int(float(current.progress) * 100)),
            )
        except Exception:
            self.progress_value = 0
        if current.progress:
            self._set_progress_model(
                training_text(
                    "training.progress.value",
                    percent=self.progress_value,
                    epoch=current.epoch_progress,
                )
            )
        else:
            self._set_progress_model(training_text("training.progress.waiting"))
        self._set_selected_values(
            (
                current.base_model,
                current.profile,
                current.dataset_version,
                current.mode,
            )
        )
        registry_note = training_text("training.metric.note.registry")
        self.stat_cards = (
            _training_metric(
                training_text("training.metric.epoch"),
                current.epoch_progress,
                registry_note,
            ),
            _training_metric(
                training_text("training.metric.loss"),
                current.loss,
                registry_note,
            ),
            _training_metric(
                training_text("training.metric.speed"),
                current.speed,
                registry_note,
            ),
            _training_metric(
                training_text("training.metric.checkpoints"),
                current.checkpoints_count,
                registry_note,
            ),
        )
        checkpoints_count = (
            int(current.checkpoints_count)
            if current.checkpoints_count.isdigit()
            else 0
        )
        checkpoint_rows = [
            _checkpoint_view(
                f"chk_{idx + 1:03d}",
                training_text("training.checkpoint.registry_note"),
                highlighted=idx == checkpoints_count - 1,
            )
            for idx in range(max(0, checkpoints_count))
        ]
        if current.artifact_path:
            checkpoint_rows.append(
                _checkpoint_view(
                    training_text("training.checkpoint.artifact"),
                    current.artifact_path,
                    highlighted=(
                        current.status_code is TrainingRunStatus.COMPLETED
                    ),
                )
            )
        self.checkpoints = tuple(checkpoint_rows) or _empty_checkpoints()
        repo_logs = self.training_service.list_training_run_logs(
            current.run_id
        )
        if repo_logs:
            self._set_log_models(tuple(repo_logs))
        else:
            self._set_log_models(
                (
                    training_text(
                        "training.log.registry.run",
                        value=current.run_id,
                    ),
                    training_text(
                        "training.log.registry.status",
                        value=current.status,
                    ),
                    training_text(
                        "training.log.registry.progress",
                        value=current.epoch_progress,
                    ),
                    training_text(
                        "training.log.registry.loss",
                        value=current.loss,
                    ),
                    training_text(
                        "training.log.registry.speed",
                        value=current.speed,
                    ),
                )
            )
        self._set_risk_models(
            training_text("training.risk.title.run_control"),
            training_text("training.risk.body.registry"),
            training_text("training.next.after_run"),
        )

    def _apply_model_versions_connector(self) -> None:
        if self.model_versions_service is None:
            return

        try:
            versions = self.model_versions_service.list_model_versions()
        except Exception:
            self._set_versions_status_model(
                training_text("training.version.error.note")
            )
            self.personality_versions = (
                _personality_version(
                    training_text("training.version.error.title"),
                    training_text("training.version.error.status"),
                    training_text("training.version.error.note"),
                    status_code="error",
                    state="error",
                ),
            )
            return
        if not versions:
            self._set_versions_status_model(
                training_text("training.version.empty.note")
            )
            self.personality_versions = _empty_versions()
            return
        self._set_versions_status_model(None)
        rows: list[PersonalityVersionView] = []
        for item in versions:
            note = (
                f"{item.base_model} · {item.profile_title} · "
                f"{item.dataset_title} · {item.training_run_id}\n"
                f"{item.quality_summary}\n{item.artifact_path}"
            )
            rows.append(
                _personality_version(
                    training_text(
                        "training.version.title",
                        title=item.title,
                    ),
                    self._version_status_text(
                        item.status_code,
                        item.status,
                    ),
                    note,
                    status_code=item.status_code.value,
                    raw_title=item.title,
                    raw_status=item.status,
                    raw_note=note,
                )
            )
        self.personality_versions = tuple(rows)

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
        self._set_local_model_state(
            LocalModelStatus.CHECKING,
            training_text("training.local_model.status.checking"),
            training_text("training.local_model.note.checking"),
        )
        self.local_inference_status = ""
        self.local_inference_status_code = LocalModelStatus.UNKNOWN
        self._local_inference_status_model = None

        if self.local_model_service is None:
            self._set_local_model_state(
                LocalModelStatus.CHECK_FAILED,
                training_text("training.local_model.status.check_failed"),
                training_text(
                    "training.local_model.note.service_unavailable"
                ),
            )
            return
        try:
            result = self.local_model_service.probe_model_files()
            status_code = normalize_local_model_status(result.status)
            self._set_local_model_state(
                status_code,
                self._local_status_text(status_code, result.status),
                result.details,
                raw_status=result.status,
                raw_note=result.details,
            )
        except Exception:
            self._set_local_model_state(
                LocalModelStatus.CHECK_FAILED,
                training_text("training.local_model.status.check_failed"),
                training_text("training.local_model.note.check_failed"),
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
        self.local_inference_status_code = LocalModelStatus.GENERATING
        self._local_inference_status_model = training_text(
            "training.local_model.status.generating"
        )
        self.local_inference_status = _base_training_text(
            self._local_inference_status_model
        )
        self.inference_response = ""
        return True, smoke_prompt

    def run_local_inference_sync(self, prompt: str) -> tuple[str, str]:
        if self.local_model_service is None:
            return LocalModelStatus.INFERENCE_UNAVAILABLE.value, ""
        try:
            result = self.local_model_service.generate_smoke(prompt)
            return result.status, (result.response or result.message)
        except Exception:
            return LocalModelStatus.GENERATION_FAILED.value, ""

    def finish_local_inference(self, status: str, response: str) -> None:
        self.inference_in_progress = False
        status_code = self._coerce_local_status(status)
        self.local_inference_status_code = status_code
        self._local_inference_status_model = self._local_status_text(
            status_code,
            status,
        )
        self.local_inference_status = (
            _base_training_text(self._local_inference_status_model)
            if status in LocalModelStatus._value2member_map_
            else status
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
                self._set_log_models(tuple(logs))

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
        self.status_code = TrainingRunStatus.RUNNING.value
        self._set_status_model(training_text("training.status.running"))
        self.creation_message = "started"
        self._creation_message_model = training_text(
            "training.message.started"
        )
        return True

    def finish_training_run(self, success: bool, message: str) -> None:
        self.training_in_progress = False
        self.creation_message = message
        self._creation_message_model = self._message_from_legacy(
            message,
            success=success,
        )
        self.refresh()
        if self.current_run_id and self.training_service is not None:
            logs = self.training_service.list_training_run_logs(
                self.current_run_id
            )
            if logs:
                self._set_log_models(tuple(logs))

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
                self._set_log_models(tuple(logs))
        return finished

    def poll_current_run(self) -> None:
        self.refresh()
        if self.current_run_id and self.training_service is not None:
            logs = self.training_service.list_training_run_logs(
                self.current_run_id
            )
            if logs:
                self._set_log_models(tuple(logs))

    def header_title_model(self) -> TrainingTextValue:
        return self._title_model

    def header_subtitle_model(self) -> TrainingTextValue:
        return self._subtitle_model

    def status_model(self) -> TrainingTextValue:
        return self._status_model

    def progress_model(self) -> TrainingTextValue:
        return self._progress_model

    def log_models(self) -> tuple[TrainingTextValue, ...]:
        return self._log_models

    def monitor_models(
        self,
    ) -> tuple[tuple[TrainingText, int, TrainingTextValue], ...]:
        return self._monitor_models

    def risk_title_model(self) -> TrainingTextValue:
        return self._risk_title_model

    def risk_body_model(self) -> TrainingTextValue:
        return self._risk_body_model

    def next_step_model(self) -> TrainingTextValue:
        return self._next_step_model

    def versions_status_model(self) -> TrainingTextValue | None:
        return self._versions_status_model

    def current_message(self) -> TrainingTextValue | None:
        return self._creation_message_model

    def local_model_status_model(self) -> TrainingTextValue:
        return self._local_model_status_model

    def local_model_note_model(self) -> TrainingTextValue:
        return self._local_model_note_model

    def local_inference_status_model(
        self,
    ) -> TrainingTextValue | None:
        return self._local_inference_status_model

    @staticmethod
    def metric_title_model(
        metric: TrainingMetric,
    ) -> TrainingTextValue:
        if metric.title_model is not None:
            return metric.title_model
        return training_text(metric.title_key) if metric.title_key else metric.title

    @staticmethod
    def metric_note_model(
        metric: TrainingMetric,
    ) -> TrainingTextValue:
        if metric.note_model is not None:
            return metric.note_model
        return training_text(metric.note_key) if metric.note_key else metric.note

    @staticmethod
    def checkpoint_name_model(
        checkpoint: CheckpointView,
    ) -> TrainingTextValue:
        if checkpoint.name_model is not None:
            return checkpoint.name_model
        return (
            training_text(checkpoint.name_key)
            if checkpoint.name_key
            else checkpoint.name
        )

    @staticmethod
    def checkpoint_note_model(
        checkpoint: CheckpointView,
    ) -> TrainingTextValue:
        if checkpoint.note_model is not None:
            return checkpoint.note_model
        return (
            training_text(checkpoint.note_key)
            if checkpoint.note_key
            else checkpoint.note
        )

    @staticmethod
    def version_title_model(
        version: PersonalityVersionView,
    ) -> TrainingTextValue:
        if version.title_model is not None:
            return version.title_model
        return version.title

    @staticmethod
    def version_status_model(
        version: PersonalityVersionView,
    ) -> TrainingTextValue:
        if version.status_model is not None:
            return version.status_model
        return version.status

    @staticmethod
    def version_note_model(
        version: PersonalityVersionView,
    ) -> TrainingTextValue:
        if version.note_model is not None:
            return version.note_model
        return version.note

    @staticmethod
    def dataset_status_model(
        dataset: TrainingDatasetChoice,
    ) -> TrainingTextValue:
        key = _DATASET_STATUS_KEYS.get(dataset.status_code)
        if key is not None:
            return training_text(key)
        return training_text("training.raw", value=dataset.status)

    @staticmethod
    def selected_object_models(
        selected_objects: tuple[tuple[str, str], ...],
    ) -> tuple[tuple[TrainingText, str], ...]:
        return tuple(
            (training_text(key), value)
            for key, (_legacy, value) in zip(
                _SELECTED_OBJECT_KEYS,
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
    def _version_status_text(
        status_code: ModelVersionStatus,
        raw_status: str,
    ) -> TrainingText:
        key = _MODEL_VERSION_STATUS_KEYS.get(status_code)
        if key is not None:
            return training_text(key)
        return training_text(
            "training.version.status.unknown",
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
    def _coerce_local_status(status: str) -> LocalModelStatus:
        try:
            return LocalModelStatus(status)
        except ValueError:
            return normalize_local_model_status(status)

    @staticmethod
    def _action_result_model(result: ActionResult) -> TrainingText:
        key = _ACTION_CODE_KEYS.get(
            result.code,
            "training.message.result_unavailable",
        )
        return training_text(key, **dict(result.values))

    @staticmethod
    def _message_from_legacy(
        message: str,
        *,
        success: bool = False,
    ) -> TrainingText:
        code_key = _ACTION_CODE_KEYS.get(message.strip())
        if code_key is not None:
            return training_text(code_key)
        key = _LEGACY_MESSAGE_KEYS.get(message)
        if key is not None:
            return training_text(key)
        if message.startswith("Запуск временно недоступен:"):
            return training_text("training.message.resource_busy")
        if message.startswith("Обучение остановлено безопасно"):
            return training_text("training.message.safe_stop")
        if success:
            return training_text("training.message.started")
        return training_text("training.message.result_unavailable")
