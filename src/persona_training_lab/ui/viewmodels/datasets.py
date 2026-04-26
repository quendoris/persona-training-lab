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
    linked_profile: str
    quality_summary: str
    readiness: str
    schema_name: str
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

    def __post_init__(self) -> None:
        self._apply_datasets_connector()

    def _apply_datasets_connector(self) -> None:
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
                    linked_profile="—",
                    quality_summary=message,
                    readiness=message,
                    schema_name="persona_json_v1",
                    preview_rows=(
                        DatasetPreviewRow("—", message, "—", "—"),
                    ),
                    validation_signals=(
                        ValidationSignal("Состояние реестра", message, "note"),
                    ),
                ),
            ),
        )

    def _map_summary(self, summary: object) -> DatasetView:
        dataset_id = getattr(summary, "dataset_id", "")
        title = getattr(summary, "title", "")
        subtitle = getattr(summary, "subtitle", "")
        status = getattr(summary, "status", "")
        record_count = getattr(summary, "record_count", 0)
        linked_profile = getattr(summary, "linked_profile", "")
        quality_summary = getattr(summary, "quality_summary", "")
        readiness = getattr(summary, "readiness", "")
        schema_name = getattr(summary, "schema_name", "")

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
                    linked_profile=linked_profile,
                    quality_summary=quality_summary,
                    readiness=readiness,
                    schema_name=schema_name,
                    preview_rows=(
                        DatasetPreviewRow(
                            "#001",
                            f"{title}: базовый срез",
                            "устойчивость, характер",
                            "—",
                        ),
                    ),
                    validation_signals=(
                        ValidationSignal(
                            "Сводка из реестра",
                            f"{status} · {record_count} записей",
                            "ok" if status == "одобрен" else "note",
                        ),
                    ),
                ),
            ),
        )

    def datasets(self) -> list[tuple[str, str, str, int]]:
        result = []
        for dataset in self._datasets:
            active_version = dataset.versions[0]
            result.append((dataset.dataset_id, dataset.title, active_version.status, len(dataset.versions)))
        return result

    def select_dataset(self, dataset_id: str) -> None:
        self._current_dataset_id = dataset_id
        dataset = self.current_dataset()
        self._current_version_id = dataset.versions[0].version_id

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
        return [
            (version.version_id, version.label, version.status, version.record_count)
            for version in self.current_dataset().versions
        ]

    def header_summary(self) -> tuple[str, str]:
        dataset = self.current_dataset()
        version = self.current_version()
        return dataset.title, f"{dataset.subtitle} · {version.label} · {version.record_count} записей"

    def right_summary(self) -> list[tuple[str, str]]:
        version = self.current_version()
        return [
            ("Статус", version.status),
            ("Готовность", version.readiness),
            ("Профиль", version.linked_profile),
            ("Схема", version.schema_name),
        ]

    def next_step(self) -> str:
        version = self.current_version()
        if version.status == "одобрен":
            return "Использовать эту версию в новом запуске обучения или сравнить с baseline."
        if version.status == "проверяется":
            return "Перезапустить валидацию и закрыть semantic warning перед одобрением."
        if version.status == "черновик":
            return "Дописать набор и прогнать полную validation pipeline."
        return "Оставить как reference-версию и сравнивать с более сильными наборами."
