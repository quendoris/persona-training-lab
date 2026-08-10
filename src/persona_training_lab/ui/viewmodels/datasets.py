from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.messages import ActionResult


_STATUS_ALIASES = {
    "одобрен для обучения": "approved",
    "одобрен": "approved",
    "approved for training": "approved",
    "approved": "approved",
    "готов к обучению": "ready",
    "готово": "ready",
    "ready for training": "ready",
    "ready": "ready",
    "ошибка структуры": "structure_error",
    "structure error": "structure_error",
    "не удалось проверить датасет": "validation_failed",
    "validation failed": "validation_failed",
    "не проверен": "unchecked",
    "not validated": "unchecked",
    "пусто": "empty",
    "empty": "empty",
}
_STATUS_KEYS = {
    "approved": "datasets.status.approved",
    "ready": "datasets.status.ready",
    "structure_error": "datasets.status.structure_error",
    "validation_failed": "datasets.status.validation_failed",
    "unchecked": "datasets.status.unchecked",
    "empty": "datasets.status.empty",
}
_DATASET_ACTION_KEYS = {
    "approved": "datasets.message.approved",
    "approval_blocked": "datasets.message.approve_blocked",
    "not_found": "datasets.error.not_found",
    "version_compare_unavailable": "datasets.action.compare_unavailable",
}


@dataclass(frozen=True, slots=True)
class DatasetText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


def dataset_text(key: str, **values: object) -> DatasetText:
    return DatasetText(key, MappingProxyType(dict(values)))


def _base_dataset_text(value: DatasetText | str | object) -> str:
    """Render only the historical base-locale compatibility projection."""

    if not isinstance(value, DatasetText):
        return str(value)
    from persona_training_lab.ui.i18n.text import text as localized_text

    rendered_values = {
        key: _base_dataset_text(item) if isinstance(item, DatasetText) else item
        for key, item in value.values.items()
    }
    count_value = rendered_values.pop("count", None)
    count = count_value if isinstance(count_value, int) else None
    return localized_text(
        None,
        value.key,
        count=count,
        **rendered_values,
    )


def _dataset_action_text(
    result: ActionResult,
    *,
    fallback_key: str,
) -> DatasetText:
    return dataset_text(
        _DATASET_ACTION_KEYS.get(result.code, fallback_key),
        **dict(result.values),
    )


@dataclass(slots=True, frozen=True)
class DatasetPreviewRow:
    row_id: str
    input_summary: str | DatasetText
    traits: str
    quality: str | DatasetText


@dataclass(slots=True, frozen=True)
class ValidationSignal:
    title: DatasetText
    body: DatasetText
    state: str  # ok | warning | note


@dataclass(slots=True, frozen=True)
class DatasetVersionView:
    version_id: str
    label: str
    status: str
    status_code: str
    record_count: int
    valid_count: int
    invalid_count: int
    linked_profile: str
    quality_summary: DatasetText
    readiness: DatasetText
    schema_name: str
    validation_errors_preview: str
    preview_rows: tuple[DatasetPreviewRow, ...]
    validation_signals: tuple[ValidationSignal, ...]


@dataclass(slots=True, frozen=True)
class DatasetView:
    dataset_id: str
    title: str
    subtitle: DatasetText
    versions: tuple[DatasetVersionView, ...]


@dataclass(slots=True)
class DatasetsViewModel:
    datasets_service: DatasetsService | None = None
    _datasets: tuple[DatasetView, ...] = field(default_factory=tuple)
    _current_dataset_id: str = ""
    _current_version_id: str = ""
    _message: DatasetText | None = None
    _legacy_message: str = ""

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self._apply_datasets_connector()

    def add_dataset_from_path(self, file_path: str) -> tuple[bool, str]:
        if self.datasets_service is None:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.load_failed"),
                "Не удалось загрузить датасеты",
            )
        try:
            created = self.datasets_service.add_dataset_from_path(file_path)
        except ValueError as exc:
            key = {
                "Файл датасета не найден": "datasets.error.file_not_found",
                "Поддерживается только формат .jsonl": "datasets.error.only_jsonl",
            }.get(str(exc), "datasets.error.add_failed")
            return self._set_action_result(False, dataset_text(key), str(exc))
        except Exception:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.add_failed"),
                "Не удалось загрузить датасеты",
            )
        message = dataset_text("datasets.message.added", title=created.title)
        legacy = f"Добавлен датасет: {created.title}"
        self._set_action_result(True, message, legacy)
        self._apply_datasets_connector(select_dataset_id=created.dataset_id)
        return True, legacy

    def validate_current_dataset(self) -> tuple[bool, str]:
        if self.datasets_service is None:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.validate_failed"),
                "Не удалось проверить датасет",
            )
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return self._set_action_result(
                False,
                dataset_text("datasets.empty.registry"),
                "Датасеты пока не добавлены",
            )
        try:
            result = self.datasets_service.validate_dataset(dataset_id)
        except Exception:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.validate_failed"),
                "Не удалось проверить датасет",
            )
        status = self.status_text(result.status)
        message = dataset_text(
            "datasets.message.validation_summary",
            status=status,
            total=result.total_rows,
            valid=result.valid_rows,
            invalid=result.invalid_rows,
        )
        legacy = (
            f"Структура: {result.status} · Записей: {result.total_rows} · "
            f"Валидных: {result.valid_rows} · Ошибок: {result.invalid_rows}"
        )
        self._set_action_result(
            result.status == "Готов к обучению",
            message,
            legacy,
        )
        self._apply_datasets_connector(select_dataset_id=dataset_id)
        return result.status == "Готов к обучению", legacy

    def approve_current_dataset(self) -> tuple[bool, str]:
        if self.datasets_service is None:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.approve_failed"),
                "Не удалось одобрить датасет",
            )
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return self._set_action_result(
                False,
                dataset_text("datasets.empty.registry"),
                "Датасеты пока не добавлены",
            )
        try:
            result = self.datasets_service.approve_dataset(dataset_id)
        except Exception:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.approve_failed"),
                "Не удалось одобрить датасет",
            )
        semantic = _dataset_action_text(
            result,
            fallback_key="datasets.error.approve_failed",
        )
        self._message = semantic
        self._legacy_message = ""
        self._apply_datasets_connector(select_dataset_id=dataset_id)
        return result.ok, result.code

    def compare_current_versions(self) -> tuple[bool, str]:
        if self.datasets_service is None:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.compare_failed"),
                "Не удалось сравнить версии",
            )
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return self._set_action_result(
                False,
                dataset_text("datasets.empty.registry"),
                "Датасеты пока не добавлены",
            )
        try:
            result = self.datasets_service.compare_dataset_versions(dataset_id)
        except Exception:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.compare_failed"),
                "Не удалось сравнить версии",
            )
        self._message = _dataset_action_text(
            result,
            fallback_key="datasets.error.compare_failed",
        )
        self._legacy_message = ""
        return result.ok, result.code

    def current_message(self) -> DatasetText | None:
        return self._message

    def _set_action_result(
        self,
        ok: bool,
        message: DatasetText,
        legacy: str,
    ) -> tuple[bool, str]:
        self._message = message
        self._legacy_message = legacy
        return ok, legacy

    def _apply_datasets_connector(
        self,
        select_dataset_id: str | None = None,
    ) -> None:
        if self.datasets_service is None:
            self._datasets = (
                self._empty_dataset_view("datasets.empty.registry"),
            )
            self._set_current_from_first()
            return
        try:
            summaries = self.datasets_service.list_datasets()
        except Exception:
            self._datasets = (
                self._empty_dataset_view("datasets.error.load_failed"),
            )
            self._set_current_from_first()
            return
        if not summaries:
            self._datasets = (
                self._empty_dataset_view("datasets.empty.registry"),
            )
            self._set_current_from_first()
            return
        self._datasets = tuple(
            self._map_summary(summary) for summary in summaries
        )
        if select_dataset_id is not None:
            for dataset in self._datasets:
                if dataset.dataset_id == select_dataset_id:
                    self._current_dataset_id = dataset.dataset_id
                    self._current_version_id = dataset.versions[0].version_id
                    return
        self._set_current_from_first()

    def _set_current_from_first(self) -> None:
        first_dataset = self._datasets[0]
        self._current_dataset_id = first_dataset.dataset_id
        self._current_version_id = first_dataset.versions[0].version_id

    def _empty_dataset_view(self, message_key: str) -> DatasetView:
        message = dataset_text(message_key)
        return DatasetView(
            dataset_id="datasets_empty",
            title=_base_dataset_text(dataset_text("datasets.title")),
            subtitle=message,
            versions=(
                DatasetVersionView(
                    version_id="datasets_empty_v1",
                    label="v1",
                    status=_base_dataset_text(
                        dataset_text("datasets.status.empty")
                    ),
                    status_code="empty",
                    record_count=0,
                    valid_count=0,
                    invalid_count=0,
                    linked_profile="—",
                    quality_summary=message,
                    readiness=message,
                    schema_name="jsonl_finetune_v1",
                    validation_errors_preview="",
                    preview_rows=(
                        DatasetPreviewRow("—", message, "—", message),
                    ),
                    validation_signals=(
                        ValidationSignal(
                            dataset_text("datasets.signal.registry.title"),
                            message,
                            "note",
                        ),
                    ),
                ),
            ),
        )

    def _map_summary(self, summary: object) -> DatasetView:
        dataset_id = getattr(summary, "dataset_id", "")
        title = getattr(summary, "title", "")
        subtitle = getattr(summary, "subtitle", "")
        status = getattr(summary, "status", "")
        status_code = self.status_code(status)
        record_count = int(getattr(summary, "record_count", 0) or 0)
        valid_count = int(getattr(summary, "valid_count", 0) or 0)
        invalid_count = int(getattr(summary, "invalid_count", 0) or 0)
        errors_preview = getattr(summary, "validation_errors_preview", "")
        format_name = getattr(summary, "format", "jsonl")

        state = (
            "ok"
            if status_code in {"ready", "approved"}
            else "warning"
            if status_code in {"structure_error", "validation_failed"}
            else "note"
        )
        status_text = self.status_text(status)
        signals = [
            ValidationSignal(
                dataset_text("datasets.signal.structure.title"),
                dataset_text(
                    "datasets.signal.structure.body",
                    status=status_text,
                ),
                state,
            ),
            ValidationSignal(
                dataset_text("datasets.signal.counts.title"),
                dataset_text(
                    "datasets.signal.counts.body",
                    records=record_count,
                    valid=valid_count,
                    invalid=invalid_count,
                ),
                "note",
            ),
            ValidationSignal(
                dataset_text("datasets.signal.author_boundary.title"),
                dataset_text("datasets.signal.author_boundary.body"),
                "note",
            ),
        ]
        if status_code == "approved":
            signals.append(
                ValidationSignal(
                    dataset_text("datasets.signal.author_approval.title"),
                    dataset_text("datasets.signal.author_approval.body"),
                    "ok",
                )
            )
        elif status_code == "ready":
            signals.append(
                ValidationSignal(
                    dataset_text("datasets.signal.awaiting_author.title"),
                    dataset_text("datasets.signal.awaiting_author.body"),
                    "note",
                )
            )
        if errors_preview:
            for line in errors_preview.splitlines()[:4]:
                signals.append(
                    ValidationSignal(
                        dataset_text(
                            "datasets.signal.structure_error.title"
                        ),
                        dataset_text("datasets.raw", value=line),
                        "warning",
                    )
                )

        preview_rows = self._preview_rows_for_dataset(dataset_id)
        if not preview_rows:
            preview_rows = (
                DatasetPreviewRow(
                    "#001",
                    dataset_text("datasets.empty.input", title=title),
                    "—",
                    status_text,
                ),
            )

        return DatasetView(
            dataset_id=dataset_id,
            title=title,
            subtitle=(
                dataset_text("datasets.subtitle.local_jsonl")
                if subtitle == "Локальный JSONL датасет"
                else dataset_text("datasets.raw", value=subtitle)
            ),
            versions=(
                DatasetVersionView(
                    version_id=f"{dataset_id}_v1",
                    label="v1",
                    status=status,
                    status_code=status_code,
                    record_count=record_count,
                    valid_count=valid_count,
                    invalid_count=invalid_count,
                    linked_profile="—",
                    quality_summary=self._quality_text(
                        status_code,
                        record_count,
                        valid_count,
                        invalid_count,
                        getattr(summary, "quality_summary", ""),
                    ),
                    readiness=status_text,
                    schema_name=format_name,
                    validation_errors_preview=errors_preview,
                    preview_rows=preview_rows,
                    validation_signals=tuple(signals),
                ),
            ),
        )

    def _quality_text(
        self,
        status_code: str,
        records: int,
        valid: int,
        invalid: int,
        raw: str,
    ) -> DatasetText:
        key = {
            "approved": "datasets.quality.approved",
            "ready": "datasets.quality.ready",
            "structure_error": "datasets.quality.structure_error",
            "validation_failed": "datasets.quality.validation_failed",
            "unchecked": "datasets.quality.unchecked",
            "empty": "datasets.empty.registry",
        }.get(status_code)
        if key is None:
            return dataset_text("datasets.raw", value=raw)
        return dataset_text(
            key,
            records=records,
            valid=valid,
            invalid=invalid,
        )

    def _preview_rows_for_dataset(
        self,
        dataset_id: str,
    ) -> tuple[DatasetPreviewRow, ...]:
        if self.datasets_service is None or not dataset_id:
            return ()
        try:
            rows = self.datasets_service.preview_dataset(dataset_id, limit=25)
        except Exception:
            return ()
        return tuple(
            DatasetPreviewRow(
                row.row_id,
                row.input_summary,
                row.traits,
                row.quality,
            )
            for row in rows
        )

    def dataset_views(self) -> tuple[DatasetView, ...]:
        return self._datasets

    def datasets(self) -> list[tuple[str, str, str, int]]:
        return [
            (
                dataset.dataset_id,
                dataset.title,
                dataset.versions[0].status,
                len(dataset.versions),
            )
            for dataset in self._datasets
        ]

    def select_dataset(self, dataset_id: str) -> None:
        self._current_dataset_id = dataset_id
        self._current_version_id = self.current_dataset().versions[0].version_id

    def select_version(self, version_id: str) -> None:
        self._current_version_id = version_id

    def current_dataset(self) -> DatasetView:
        for dataset in self._datasets:
            if dataset.dataset_id == self._current_dataset_id:
                return dataset
        return self._datasets[0]

    def current_version(self) -> DatasetVersionView:
        dataset = self.current_dataset()
        for version in dataset.versions:
            if version.version_id == self._current_version_id:
                return version
        return dataset.versions[0]

    def version_views(self) -> tuple[DatasetVersionView, ...]:
        return self.current_dataset().versions

    def versions(self) -> list[tuple[str, str, str, int]]:
        return [
            (
                version.version_id,
                version.label,
                version.status,
                version.record_count,
            )
            for version in self.current_dataset().versions
        ]

    def header_summary_model(self) -> tuple[str, DatasetText]:
        dataset = self.current_dataset()
        version = self.current_version()
        if self._message is not None:
            return dataset.title, self._message
        return (
            dataset.title,
            dataset_text(
                "datasets.header.summary",
                subtitle=dataset.subtitle,
                version=version.label,
                records=dataset_text(
                    "datasets.count.records",
                    count=version.record_count,
                ),
            ),
        )

    def header_summary(self) -> tuple[str, str]:
        title, summary = self.header_summary_model()
        return title, _base_dataset_text(summary)

    def right_summary_model(self) -> tuple[tuple[str, object], ...]:
        version = self.current_version()
        return (
            ("datasets.summary.status", self.status_text(version.status)),
            ("datasets.summary.records", version.record_count),
            ("datasets.summary.valid", version.valid_count),
            ("datasets.summary.errors", version.invalid_count),
            ("datasets.summary.format", version.schema_name),
        )

    def right_summary(self) -> list[tuple[str, str]]:
        return [
            (
                _base_dataset_text(dataset_text(key)),
                _base_dataset_text(value),
            )
            for key, value in self.right_summary_model()
        ]

    def next_step_model(self) -> DatasetText:
        code = self.current_version().status_code
        key = {
            "approved": "datasets.next.approved",
            "ready": "datasets.next.ready",
            "structure_error": "datasets.next.structure_error",
            "validation_failed": "datasets.next.validation_failed",
        }.get(code, "datasets.next.empty")
        return dataset_text(key)

    def next_step(self) -> str:
        return _base_dataset_text(self.next_step_model())

    @staticmethod
    def status_code(status: str) -> str:
        normalized = " ".join(status.casefold().split())
        return _STATUS_ALIASES.get(normalized, "unknown")

    @classmethod
    def status_text(cls, status: str) -> DatasetText:
        code = cls.status_code(status)
        key = _STATUS_KEYS.get(code)
        if key is None:
            return dataset_text("datasets.raw", value=status)
        return dataset_text(key)
