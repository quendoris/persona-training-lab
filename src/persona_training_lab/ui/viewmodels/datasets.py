from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.datasets.service import DatasetsService


@dataclass(slots=True, frozen=True)
class DatasetPreviewRow:
    row_id: str
    input_summary: str
    traits: str
    quality: str


@dataclass(slots=True, frozen=True)
class ValidationSignal:
    title: str
    body: str
    state: str  # ok | warning | note


@dataclass(slots=True, frozen=True)
class DatasetVersionView:
    version_id: str
    label: str
    status: str
    record_count: int
    valid_count: int
    invalid_count: int
    linked_profile: str
    quality_summary: str
    readiness: str
    schema_name: str
    validation_errors_preview: str
    preview_rows: tuple[DatasetPreviewRow, ...]
    validation_signals: tuple[ValidationSignal, ...]


@dataclass(slots=True, frozen=True)
class DatasetView:
    dataset_id: str
    title: str
    subtitle: str
    versions: tuple[DatasetVersionView, ...]


@dataclass(slots=True)
class DatasetsViewModel:
    datasets_service: DatasetsService | None = None
    _datasets: tuple[DatasetView, ...] = field(default_factory=tuple)
    _current_dataset_id: str = ""
    _current_version_id: str = ""
    _message: str = ""

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self._apply_datasets_connector()

    def add_dataset_from_path(self, file_path: str) -> tuple[bool, str]:
        if self.datasets_service is None:
            return False, "Не удалось загрузить датасеты"
        try:
            created = self.datasets_service.add_dataset_from_path(file_path)
        except ValueError as exc:
            return False, str(exc)
        except Exception:
            return False, "Не удалось загрузить датасеты"
        self._message = f"Добавлен датасет: {created.title}"
        self._apply_datasets_connector(select_dataset_id=created.dataset_id)
        return True, self._message

    def validate_current_dataset(self) -> tuple[bool, str]:
        if self.datasets_service is None:
            return False, "Не удалось проверить датасет"
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return False, "Датасеты пока не добавлены"
        try:
            result = self.datasets_service.validate_dataset(dataset_id)
        except Exception:
            return False, "Не удалось проверить датасет"
        self._message = (
            f"Структура: {result.status} · Записей: {result.total_rows} · "
            f"Валидных: {result.valid_rows} · Ошибок: {result.invalid_rows}"
        )
        self._apply_datasets_connector(select_dataset_id=dataset_id)
        return result.status == "Готов к обучению", self._message

    def approve_current_dataset(self) -> tuple[bool, str]:
        if self.datasets_service is None:
            return False, "Не удалось одобрить датасет"
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return False, "Датасеты пока не добавлены"
        try:
            ok, message = self.datasets_service.approve_dataset(dataset_id)
        except Exception:
            return False, "Не удалось одобрить датасет"
        self._message = message
        self._apply_datasets_connector(select_dataset_id=dataset_id)
        return ok, message

    def compare_current_versions(self) -> tuple[bool, str]:
        if self.datasets_service is None:
            return False, "Не удалось сравнить версии"
        dataset_id = self.current_dataset().dataset_id
        if dataset_id == "datasets_empty":
            return False, "Датасеты пока не добавлены"
        try:
            ok, message = self.datasets_service.compare_dataset_versions(dataset_id)
        except Exception:
            return False, "Не удалось сравнить версии"
        self._message = message
        return ok, message

    def _apply_datasets_connector(self, select_dataset_id: str | None = None) -> None:
        if self.datasets_service is None:
            self._datasets = (self._empty_dataset_view("Датасеты пока не добавлены"),)
            self._set_current_from_first()
            return
        try:
            summaries = self.datasets_service.list_datasets()
        except Exception:
            self._datasets = (self._empty_dataset_view("Не удалось загрузить датасеты"),)
            self._set_current_from_first()
            return
        if not summaries:
            self._datasets = (self._empty_dataset_view("Датасеты пока не добавлены"),)
            self._set_current_from_first()
            return
        self._datasets = tuple(self._map_summary(summary) for summary in summaries)
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

    def _empty_dataset_view(self, message: str) -> DatasetView:
        return DatasetView(
            dataset_id="datasets_empty",
            title="Датасеты",
            subtitle=message,
            versions=(
                DatasetVersionView(
                    version_id="datasets_empty_v1",
                    label="v1",
                    status="пусто",
                    record_count=0,
                    valid_count=0,
                    invalid_count=0,
                    linked_profile="—",
                    quality_summary=message,
                    readiness=message,
                    schema_name="jsonl_finetune_v1",
                    validation_errors_preview="",
                    preview_rows=(DatasetPreviewRow("—", message, "—", "—"),),
                    validation_signals=(ValidationSignal("Состояние реестра", message, "note"),),
                ),
            ),
        )

    def _map_summary(self, summary: object) -> DatasetView:
        dataset_id = getattr(summary, "dataset_id", "")
        title = getattr(summary, "title", "")
        subtitle = getattr(summary, "subtitle", "")
        status = getattr(summary, "status", "")
        record_count = getattr(summary, "record_count", 0)
        valid_count = getattr(summary, "valid_count", 0)
        invalid_count = getattr(summary, "invalid_count", 0)
        quality_summary = getattr(summary, "quality_summary", "")
        errors_preview = getattr(summary, "validation_errors_preview", "")
        format_name = getattr(summary, "format", "jsonl")

        state = "ok" if status == "Готов к обучению" else "warning" if status in {"Ошибка структуры", "Не удалось проверить датасет"} else "note"
        signals = [
            ValidationSignal("Структурная проверка", f"Статус: {status}", state),
            ValidationSignal("Счётчики", f"Записей: {record_count} · Валидных: {valid_count} · Ошибок: {invalid_count}", "note"),
            ValidationSignal("Граница ответственности", "Автопроверка не оценивает смысл, стиль и полезность примеров. Это утверждает автор датасета.", "note"),
        ]
        if errors_preview:
            for line in errors_preview.splitlines()[:4]:
                signals.append(ValidationSignal("Ошибка структуры", line, "warning"))

        preview_rows = self._preview_rows_for_dataset(dataset_id)
        if not preview_rows:
            preview_rows = (DatasetPreviewRow("#001", f"{title}: JSONL пока не прочитан", "—", status),)

        return DatasetView(
            dataset_id=dataset_id,
            title=title,
            subtitle=subtitle,
            versions=(
                DatasetVersionView(
                    version_id=f"{dataset_id}_v1",
                    label="v1",
                    status=status,
                    record_count=record_count,
                    valid_count=valid_count,
                    invalid_count=invalid_count,
                    linked_profile="—",
                    quality_summary=quality_summary,
                    readiness=status,
                    schema_name=format_name,
                    validation_errors_preview=errors_preview,
                    preview_rows=preview_rows,
                    validation_signals=tuple(signals),
                ),
            ),
        )

    def _preview_rows_for_dataset(self, dataset_id: str) -> tuple[DatasetPreviewRow, ...]:
        if self.datasets_service is None or not dataset_id:
            return ()
        try:
            rows = self.datasets_service.preview_dataset(dataset_id, limit=25)
        except Exception:
            return ()
        return tuple(
            DatasetPreviewRow(row.row_id, row.input_summary, row.traits, row.quality)
            for row in rows
        )

    def datasets(self) -> list[tuple[str, str, str, int]]:
        return [(dataset.dataset_id, dataset.title, dataset.versions[0].status, len(dataset.versions)) for dataset in self._datasets]

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

    def versions(self) -> list[tuple[str, str, str, int]]:
        return [(version.version_id, version.label, version.status, version.record_count) for version in self.current_dataset().versions]

    def header_summary(self) -> tuple[str, str]:
        dataset = self.current_dataset()
        version = self.current_version()
        if self._message:
            return dataset.title, self._message
        return dataset.title, f"{dataset.subtitle} · {version.label} · {version.record_count} записей"

    def right_summary(self) -> list[tuple[str, str]]:
        version = self.current_version()
        return [
            ("Статус", version.status),
            ("Записей", str(version.record_count)),
            ("Валидных", str(version.valid_count)),
            ("Ошибок", str(version.invalid_count)),
            ("Формат", version.schema_name),
        ]

    def next_step(self) -> str:
        version = self.current_version()
        if version.status == "Готов к обучению":
            return "Датасет готов к обучению. Смысл примеров утверждён автором, можно запускать тренировку."
        if version.status == "Ошибка структуры":
            return "Исправьте JSONL-структуру и обязательные поля, затем повторите проверку."
        if version.status == "Не удалось проверить датасет":
            return "Проверьте путь к файлу и повторите проверку."
        return "Добавьте JSONL-файл и запустите структурную проверку."
