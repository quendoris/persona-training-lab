from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.model_versions.quality import (
    parse_model_version_quality,
)
from persona_training_lab.application.model_versions.service import (
    ModelVersionsService,
)
from persona_training_lab.domain.models.statuses import ModelVersionStatus


_STATUS_KEYS = {
    ModelVersionStatus.DRAFT: "snapshots.status.draft",
    ModelVersionStatus.READY: "snapshots.status.ready",
    ModelVersionStatus.ARCHIVED: "snapshots.status.archived",
    ModelVersionStatus.FAILED: "snapshots.status.failed",
}
_EMPTY_STATE_KEYS = {
    "service_unavailable": "snapshots.state.service_unavailable",
    "load_failed": "snapshots.state.load_failed",
    "empty": "snapshots.state.empty",
}
_EMPTY_STATUS_KEYS = {
    "service_unavailable": "snapshots.status.unavailable",
    "load_failed": "snapshots.status.error",
    "empty": "snapshots.status.empty",
}
_LEGACY_EMPTY_STATES = {
    "service_unavailable": (
        "Сервис версий модели не подключён",
        "недоступно",
    ),
    "load_failed": ("Не удалось загрузить снимки", "ошибка"),
    "empty": ("Снимки пока не созданы", "пусто"),
}


@dataclass(frozen=True, slots=True)
class SnapshotText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


def snapshot_text(key: str, **values: object) -> SnapshotText:
    return SnapshotText(key, MappingProxyType(dict(values)))


SnapshotValue = SnapshotText | str


@dataclass(slots=True, frozen=True)
class SnapshotMetric:
    title: str
    value: str
    note: str


@dataclass(slots=True, frozen=True)
class SnapshotMetricModel:
    title: SnapshotText
    value: SnapshotValue
    note: SnapshotValue


@dataclass(slots=True, frozen=True)
class SnapshotRow:
    snapshot_id: str
    title: str
    status: str
    subtitle: str
    base_model: str = ""
    profile_title: str = ""
    dataset_title: str = ""
    training_run_id: str = ""
    artifact_path: str = ""
    quality_summary: str = ""
    status_code: ModelVersionStatus = ModelVersionStatus.UNKNOWN
    state_code: str = "version"


@dataclass(slots=True, frozen=True)
class TimelineItem:
    title: str
    note: str


@dataclass(slots=True, frozen=True)
class TimelineModel:
    title: SnapshotText
    note: SnapshotValue


@dataclass(slots=True)
class SnapshotsViewModel:
    model_versions_service: ModelVersionsService | None = None
    snapshots: tuple[SnapshotRow, ...] = ()
    current_snapshot_id: str = ""

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        if self.model_versions_service is None:
            self.snapshots = (
                self._empty_snapshot("service_unavailable"),
            )
            self.current_snapshot_id = self.snapshots[0].snapshot_id
            return
        try:
            versions = self.model_versions_service.list_model_versions()
        except Exception:
            self.snapshots = (self._empty_snapshot("load_failed"),)
            self.current_snapshot_id = self.snapshots[0].snapshot_id
            return
        if not versions:
            self.snapshots = (self._empty_snapshot("empty"),)
            self.current_snapshot_id = self.snapshots[0].snapshot_id
            return

        self.snapshots = tuple(
            SnapshotRow(
                snapshot_id=item.version_id,
                title=item.title,
                status=item.status,
                subtitle=(
                    f"{item.base_model} · {item.profile_title} · "
                    f"{item.dataset_title}"
                ),
                base_model=item.base_model,
                profile_title=item.profile_title,
                dataset_title=item.dataset_title,
                training_run_id=item.training_run_id,
                artifact_path=item.artifact_path,
                quality_summary=item.quality_summary,
                status_code=item.status_code,
            )
            for item in versions
        )
        if not any(
            item.snapshot_id == self.current_snapshot_id
            for item in self.snapshots
        ):
            self.current_snapshot_id = self.snapshots[0].snapshot_id

    def _empty_snapshot(self, state_code: str) -> SnapshotRow:
        message, status = _LEGACY_EMPTY_STATES[state_code]
        return SnapshotRow(
            snapshot_id="snapshots_empty",
            title="Снимки",
            status=status,
            subtitle=message,
            quality_summary=message,
            state_code=state_code,
        )

    def select_snapshot(self, snapshot_id: str) -> None:
        if any(
            item.snapshot_id == snapshot_id for item in self.snapshots
        ):
            self.current_snapshot_id = snapshot_id

    def current_snapshot(self) -> SnapshotRow:
        for item in self.snapshots:
            if item.snapshot_id == self.current_snapshot_id:
                return item
        return self.snapshots[0]

    def row_title_model(self, row: SnapshotRow) -> SnapshotValue:
        if row.snapshot_id == "snapshots_empty":
            return snapshot_text("snapshots.screen.title")
        return row.title

    def row_tooltip_model(self, row: SnapshotRow) -> SnapshotText:
        return snapshot_text(
            "snapshots.list.tooltip",
            title=self.row_title_model(row),
            subtitle=self._subtitle_model(row),
        )

    def header_title_model(self) -> SnapshotText:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return snapshot_text("snapshots.header.title.empty")
        return snapshot_text(
            "snapshots.header.title.selected",
            title=snap.title,
        )

    def header_subtitle_model(self) -> SnapshotValue:
        return self._subtitle_model(self.current_snapshot())

    def status_model(self, row: SnapshotRow | None = None) -> SnapshotText:
        snap = row or self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return snapshot_text(
                _EMPTY_STATUS_KEYS.get(
                    snap.state_code,
                    "snapshots.status.empty",
                )
            )
        key = _STATUS_KEYS.get(snap.status_code)
        if key is not None:
            return snapshot_text(key)
        return snapshot_text(
            "snapshots.status.unknown",
            status=snap.status or "—",
        )

    def metric_models(self) -> tuple[SnapshotMetricModel, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (
                SnapshotMetricModel(
                    snapshot_text("snapshots.metric.lifecycle"),
                    self.status_model(snap),
                    self._state_model(snap),
                ),
                SnapshotMetricModel(
                    snapshot_text("snapshots.metric.source"),
                    "—",
                    snapshot_text("snapshots.metric.note.source.empty"),
                ),
                SnapshotMetricModel(
                    snapshot_text("snapshots.metric.artifact"),
                    "—",
                    snapshot_text("snapshots.metric.note.artifact.empty"),
                ),
                SnapshotMetricModel(
                    snapshot_text("snapshots.metric.readiness"),
                    "0%",
                    snapshot_text(
                        "snapshots.metric.note.readiness.empty"
                    ),
                ),
            )
        return (
            SnapshotMetricModel(
                snapshot_text("snapshots.metric.lifecycle"),
                self.status_model(snap),
                snapshot_text(
                    "snapshots.metric.note.version.registered"
                ),
            ),
            SnapshotMetricModel(
                snapshot_text("snapshots.metric.source"),
                snap.training_run_id or "—",
                snapshot_text("snapshots.metric.note.source.run"),
            ),
            SnapshotMetricModel(
                snapshot_text("snapshots.metric.artifact"),
                snapshot_text(
                    "snapshots.value.present"
                    if snap.artifact_path
                    else "snapshots.value.absent"
                ),
                (
                    snap.artifact_path
                    if snap.artifact_path
                    else snapshot_text(
                        "snapshots.metric.note.artifact.missing"
                    )
                ),
            ),
            SnapshotMetricModel(
                snapshot_text("snapshots.metric.profile"),
                snap.profile_title or "—",
                snapshot_text("snapshots.metric.note.profile"),
            ),
        )

    def timeline_models(self) -> tuple[TimelineModel, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (
                TimelineModel(
                    snapshot_text("snapshots.timeline.wait_artifact"),
                    self._state_model(snap),
                ),
            )
        return (
            TimelineModel(
                snapshot_text("snapshots.timeline.training_completed"),
                snapshot_text(
                    "snapshots.timeline.note.run",
                    run_id=snap.training_run_id or "—",
                ),
            ),
            TimelineModel(
                snapshot_text("snapshots.timeline.artifact_saved"),
                (
                    snap.artifact_path
                    if snap.artifact_path
                    else snapshot_text(
                        "snapshots.timeline.note.artifact_missing"
                    )
                ),
            ),
            TimelineModel(
                snapshot_text(
                    "snapshots.timeline.version_registered"
                ),
                self._quality_model(snap.quality_summary),
            ),
            TimelineModel(
                snapshot_text("snapshots.timeline.ready_for_tests"),
                snapshot_text(
                    "snapshots.timeline.note.ready_for_tests"
                ),
            ),
        )

    def lineage_models(self) -> tuple[SnapshotText, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (snapshot_text("snapshots.lineage.empty"),)
        return (
            snapshot_text(
                "snapshots.lineage.base_model",
                value=snap.base_model or "—",
            ),
            snapshot_text(
                "snapshots.lineage.profile",
                value=snap.profile_title or "—",
            ),
            snapshot_text(
                "snapshots.lineage.dataset",
                value=snap.dataset_title or "—",
            ),
            snapshot_text(
                "snapshots.lineage.training_run",
                value=snap.training_run_id or "—",
            ),
            snapshot_text(
                "snapshots.lineage.artifact",
                value=snap.artifact_path or "—",
            ),
        )

    def next_step_model(self) -> SnapshotText:
        snap = self.current_snapshot()
        return snapshot_text(
            "snapshots.next.empty"
            if snap.snapshot_id == "snapshots_empty"
            else "snapshots.next.ready"
        )

    def _subtitle_model(self, snap: SnapshotRow) -> SnapshotValue:
        if snap.snapshot_id == "snapshots_empty":
            return self._state_model(snap)
        return snapshot_text(
            "snapshots.header.subtitle.version",
            base_model=snap.base_model or "—",
            profile=snap.profile_title or "—",
            dataset=snap.dataset_title or "—",
        )

    def _state_model(self, snap: SnapshotRow) -> SnapshotText:
        return snapshot_text(
            _EMPTY_STATE_KEYS.get(
                snap.state_code,
                "snapshots.state.empty",
            )
        )

    def _quality_model(self, quality: str) -> SnapshotValue:
        parsed = parse_model_version_quality(quality)
        if parsed is None:
            normalized = quality.strip()
            return normalized or snapshot_text("snapshots.quality.missing")
        if parsed.code == "training_completed":
            return snapshot_text(
                "snapshots.quality.training_completed",
                loss=parsed.values.get("loss", "—"),
                checkpoints=parsed.values.get("checkpoints", "—"),
            )
        if parsed.code == "artifact_saved":
            return snapshot_text("snapshots.quality.artifact_saved")
        return snapshot_text("snapshots.quality.missing")

    def detail_metrics(self) -> tuple[tuple[str, str], ...]:
        return tuple((metric.title, metric.value) for metric in self.metrics)

    @property
    def metrics(self) -> tuple[SnapshotMetric, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (
                SnapshotMetric(
                    "Жизненный цикл",
                    snap.status,
                    snap.subtitle,
                ),
                SnapshotMetric(
                    "Источник",
                    "—",
                    "успешный full fine-tune ещё не зарегистрировал artifact",
                ),
                SnapshotMetric(
                    "Artifact",
                    "—",
                    "нет сохранённой версии модели",
                ),
                SnapshotMetric(
                    "Готовность",
                    "0%",
                    "создайте training run и дождитесь artifact",
                ),
            )
        return (
            SnapshotMetric(
                "Жизненный цикл",
                snap.status,
                "версия модели зарегистрирована после обучения",
            ),
            SnapshotMetric(
                "Источник",
                snap.training_run_id or "—",
                "training run, который создал artifact",
            ),
            SnapshotMetric(
                "Artifact",
                "есть" if snap.artifact_path else "нет",
                snap.artifact_path or "artifact path отсутствует",
            ),
            SnapshotMetric(
                "Профиль",
                snap.profile_title or "—",
                "профиль, выбранный при обучении",
            ),
        )

    def timeline_rows(self) -> tuple[tuple[str, str], ...]:
        return tuple((item.title, item.note) for item in self.timeline)

    @property
    def timeline(self) -> tuple[TimelineItem, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (TimelineItem("ожидание artifact", snap.subtitle),)
        return (
            TimelineItem(
                "обучение завершено",
                f"run: {snap.training_run_id}",
            ),
            TimelineItem(
                "artifact сохранён",
                snap.artifact_path or "artifact path отсутствует",
            ),
            TimelineItem(
                "версия модели зарегистрирована",
                snap.quality_summary or "без quality summary",
            ),
            TimelineItem(
                "готово к тестам",
                "откройте вкладку «Тесты» и запустите проверку модели",
            ),
        )

    def lineage_rows(self) -> tuple[str, ...]:
        return self.lineage

    @property
    def lineage(self) -> tuple[str, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (
                "Нет lineage: снимки появятся после успешного обучения.",
            )
        return (
            f"Базовая модель · {snap.base_model or '—'}",
            f"Профиль · {snap.profile_title or '—'}",
            f"Версия датасета · {snap.dataset_title or '—'}",
            f"Запуск обучения · {snap.training_run_id or '—'}",
            f"Artifact · {snap.artifact_path or '—'}",
        )

    def next_step(self) -> str:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (
                "Завершите обучение: после artifact снимок появится "
                "автоматически из зарегистрированной версии модели."
            )
        return (
            "Запустите тесты для этой версии модели и затем "
            "переходите к анализу результатов."
        )
