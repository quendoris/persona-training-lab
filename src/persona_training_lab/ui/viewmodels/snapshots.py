from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.model_versions.service import ModelVersionsService


@dataclass(slots=True, frozen=True)
class SnapshotMetric:
    title: str
    value: str
    note: str


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


@dataclass(slots=True, frozen=True)
class TimelineItem:
    title: str
    note: str


@dataclass(slots=True)
class SnapshotsViewModel:
    model_versions_service: ModelVersionsService | None = None
    snapshots: tuple[SnapshotRow, ...] = ()
    current_snapshot_id: str = ""

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        if self.model_versions_service is None:
            self.snapshots = (self._empty_snapshot("Сервис версий модели не подключён"),)
            self.current_snapshot_id = self.snapshots[0].snapshot_id
            return
        try:
            versions = self.model_versions_service.list_model_versions()
        except Exception:
            self.snapshots = (self._empty_snapshot("Не удалось загрузить снимки"),)
            self.current_snapshot_id = self.snapshots[0].snapshot_id
            return
        if not versions:
            self.snapshots = (self._empty_snapshot("Снимки пока не созданы"),)
            self.current_snapshot_id = self.snapshots[0].snapshot_id
            return
        self.snapshots = tuple(
            SnapshotRow(
                snapshot_id=item.version_id,
                title=item.title,
                status=item.status,
                subtitle=f"{item.base_model} · {item.profile_title} · {item.dataset_title}",
                base_model=item.base_model,
                profile_title=item.profile_title,
                dataset_title=item.dataset_title,
                training_run_id=item.training_run_id,
                artifact_path=item.artifact_path,
                quality_summary=item.quality_summary,
            )
            for item in versions
        )
        if not any(item.snapshot_id == self.current_snapshot_id for item in self.snapshots):
            self.current_snapshot_id = self.snapshots[0].snapshot_id

    def _empty_snapshot(self, message: str) -> SnapshotRow:
        return SnapshotRow(
            snapshot_id="snapshots_empty",
            title="Снимки",
            status="пусто",
            subtitle=message,
            quality_summary=message,
        )

    def select_snapshot(self, snapshot_id: str) -> None:
        self.current_snapshot_id = snapshot_id

    def current_snapshot(self) -> SnapshotRow:
        for item in self.snapshots:
            if item.snapshot_id == self.current_snapshot_id:
                return item
        return self.snapshots[0]

    def detail_metrics(self) -> tuple[tuple[str, str], ...]:
        return tuple((metric.title, metric.value) for metric in self.metrics)

    @property
    def metrics(self) -> tuple[SnapshotMetric, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (
                SnapshotMetric("Жизненный цикл", snap.status, snap.subtitle),
                SnapshotMetric("Источник", "—", "успешный full fine-tune ещё не зарегистрировал artifact"),
                SnapshotMetric("Artifact", "—", "нет сохранённой версии модели"),
                SnapshotMetric("Готовность", "0%", "создайте training run и дождитесь artifact"),
            )
        return (
            SnapshotMetric("Жизненный цикл", snap.status, "версия модели зарегистрирована после обучения"),
            SnapshotMetric("Источник", snap.training_run_id or "—", "training run, который создал artifact"),
            SnapshotMetric("Artifact", "есть" if snap.artifact_path else "нет", snap.artifact_path or "artifact path отсутствует"),
            SnapshotMetric("Профиль", snap.profile_title or "—", "профиль, выбранный при обучении"),
        )

    def timeline_rows(self) -> tuple[tuple[str, str], ...]:
        return tuple((item.title, item.note) for item in self.timeline)

    @property
    def timeline(self) -> tuple[TimelineItem, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return (TimelineItem("ожидание artifact", snap.subtitle),)
        return (
            TimelineItem("обучение завершено", f"run: {snap.training_run_id}"),
            TimelineItem("artifact сохранён", snap.artifact_path or "artifact path отсутствует"),
            TimelineItem("версия модели зарегистрирована", snap.quality_summary or "без quality summary"),
            TimelineItem("готово к тестам", "откройте вкладку «Тесты» и запустите проверку модели"),
        )

    def lineage_rows(self) -> tuple[str, ...]:
        return self.lineage

    @property
    def lineage(self) -> tuple[str, ...]:
        snap = self.current_snapshot()
        if snap.snapshot_id == "snapshots_empty":
            return ("Нет lineage: снимки появятся после успешного обучения.",)
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
            return "Завершите обучение: после artifact снимок появится автоматически из зарегистрированной версии модели."
        return "Запустите тесты для этой версии модели и затем переходите к анализу результатов."
