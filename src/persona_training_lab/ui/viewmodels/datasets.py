from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.datasets.diagnostics import (
    DatasetDiagnostic,
    decode_dataset_diagnostic,
)
from persona_training_lab.application.datasets.errors import (
    DatasetServiceError,
    DatasetServiceErrorCode,
)
from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.messages import ActionResult


_STATUS_ALIASES = {
    "approved_for_training": "approved",
    "одобрен для обучения": "approved",
    "одобрен": "approved",
    "approved for training": "approved",
    "approved": "approved",
    "validated": "ready",
    "готов к обучению": "ready",
    "готово": "ready",
    "ready for training": "ready",
    "ready": "ready",
    "structure_error": "structure_error",
    "ошибка структуры": "structure_error",
    "structure error": "structure_error",
    "validation_failed": "validation_failed",
    "не удалось проверить датасет": "validation_failed",
    "validation failed": "validation_failed",
    "imported": "unchecked",
    "draft": "unchecked",
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
_DATASET_SERVICE_ERROR_KEYS = {
    DatasetServiceErrorCode.FILE_NOT_FOUND: "datasets.error.file_not_found",
    DatasetServiceErrorCode.ONLY_JSONL: "datasets.error.only_jsonl",
    DatasetServiceErrorCode.SAVE_FAILED: "datasets.error.add_failed",
    DatasetServiceErrorCode.NOT_FOUND: "datasets.error.not_found",
}
_DIAGNOSTIC_KEYS = {
    "file_not_found": "datasets.error.file_not_found",
    "only_jsonl": "datasets.error.only_jsonl",
    "invalid_json": "datasets.diagnostic.invalid_json",
    "record_not_object": "datasets.diagnostic.record_not_object",
    "messages_not_list": "datasets.diagnostic.messages_not_list",
    "message_not_object": "datasets.diagnostic.message_not_object",
    "invalid_role": "datasets.diagnostic.invalid_role",
    "content_empty": "datasets.diagnostic.content_empty",
    "messages_missing_pair": "datasets.diagnostic.messages_missing_pair",
    "instruction_empty": "datasets.diagnostic.instruction_empty",
    "output_empty": "datasets.diagnostic.output_empty",
    "input_not_string": "datasets.diagnostic.input_not_string",
    "prompt_empty": "datasets.diagnostic.prompt_empty",
    "response_empty": "datasets.diagnostic.response_empty",
    "unsupported_schema": "datasets.diagnostic.unsupported_schema",
    "empty_file": "datasets.diagnostic.empty_file",
}
_PREVIEW_QUALITY_KEYS = {
    "structure_ok": "datasets.preview.quality.structure_ok",
    "structure_error": "datasets.preview.quality.structure_error",
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


def _dataset_service_error_text(
    error: DatasetServiceError,
    *,
    fallback: DatasetText,
) -> DatasetText:
    key = _DATASET_SERVICE_ERROR_KEYS.get(error.code)
    return dataset_text(key) if key is not None else fallback


def _dataset_diagnostic_text(value: DatasetDiagnostic | str) -> DatasetText:
    diagnostic = (
        value
        if isinstance(value, DatasetDiagnostic)
        else decode_dataset_diagnostic(value)
    )
    if diagnostic is None:
        return dataset_text("datasets.raw", value=value)
    key = _DIAGNOSTIC_KEYS.get(diagnostic.code)
    message = (
        dataset_text(key, **dict(diagnostic.values))
        if key is not None
        else dataset_text("datasets.diagnostic.unknown")
    )
    if diagnostic.line is None:
        return message
    return dataset_text(
        "datasets.diagnostic.line",
        line=diagnostic.line,
        message=message,
    )


def _preview_quality_text(value: str) -> DatasetText:
    key = _PREVIEW_QUALITY_KEYS.get(value)
    if key is not None:
        return dataset_text(key)
    normalized = value.strip()
    if (
        normalized
        and normalized.isascii()
        and normalized.replace("_", "").isalnum()
        and normalized == normalized.casefold()
    ):
        return dataset_text("datasets.preview.quality.unknown")
    return dataset_text("datasets.raw", value=value)


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
            )
        try:
            created = self.datasets_service.add_dataset_from_path(file_path)
        except DatasetServiceError as exc:
            return self._set_action_result(
                False,
                _dataset_service_error_text(
                    exc,
                    fallback=dataset_text("datasets.error.add_failed"),
                ),
            )
        except Exception:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.add_failed"),
            )
        message = dataset_text("datasets.message.added", title=created.title)
        ok, legacy = self._set_action_result(True, message)
        self._apply_datasets_connector(select_dataset_id=created.dataset_id)
        return ok, legacy

    def validate_current_dataset(self) -> tuple[bool, str]:
        if self.datasets_service is None:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.validate_failed"),
            )
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return self._set_action_result(
                False,
                dataset_text("datasets.empty.registry"),
            )
        try:
            result = self.datasets_service.validate_dataset(dataset_id)
        except DatasetServiceError as exc:
            return self._set_action_result(
                False,
                _dataset_service_error_text(
                    exc,
                    fallback=dataset_text("datasets.error.validate_failed"),
                ),
            )
        except Exception:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.validate_failed"),
            )
        status = self.status_text(result.status)
        message = dataset_text(
            "datasets.message.validation_summary",
            status=status,
            total=result.total_rows,
            valid=result.valid_rows,
            invalid=result.invalid_rows,
        )
        is_ready = self.status_code(result.status) == "ready"
        ok, legacy = self._set_action_result(is_ready, message)
        self._apply_datasets_connector(select_dataset_id=dataset_id)
        return ok, legacy

    def approve_current_dataset(self) -> tuple[bool, str]:
        if self.datasets_service is None:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.approve_failed"),
            )
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return self._set_action_result(
                False,
                dataset_text("datasets.empty.registry"),
            )
        try:
            result = self.datasets_service.approve_dataset(dataset_id)
        except DatasetServiceError as exc:
            return self._set_action_result(
                False,
                _dataset_service_error_text(
                    exc,
                    fallback=dataset_text("datasets.error.approve_failed"),
                ),
            )
        except Exception:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.approve_failed"),
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
            )
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return self._set_action_result(
                False,
                dataset_text("datasets.empty.registry"),
            )
        try:
            result = self.datasets_service.compare_dataset_versions(dataset_id)
        except Exception:
            return self._set_action_result(
                False,
                dataset_text("datasets.error.compare_failed"),
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
    ) -> tuple[bool, str]:
        legacy = _base_dataset_text(message)
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
                        _dataset_diagnostic_text(line),
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
                if (
                    subtitle == "Локальный JSONL датасет"
                    or (not subtitle and format_name == "jsonl")
                )
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
                (
                    _dataset_diagnostic_text(row.input_summary)
                    if isinstance(row.input_summary, DatasetDiagnostic)
                    else row.input_summary
                ),
                row.traits,
                _preview_quality_text(row.quality),
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
