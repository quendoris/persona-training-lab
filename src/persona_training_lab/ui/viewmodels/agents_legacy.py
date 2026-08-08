from __future__ import annotations

from persona_training_lab.ui.viewmodels.agents_contracts import (
    PortraitStats,
    VersionNodeView,
)
from persona_training_lab.ui.viewmodels.agents_guidance import (
    AgentsGuidanceViewModel,
)


class AgentsViewModel(AgentsGuidanceViewModel):
    """Compatibility VM retaining the pre-atomic canonical graph projection."""

    def version_nodes(self) -> tuple[VersionNodeView, ...]:
        training_runs = self._training_runs()
        versions = self._model_versions()
        datasets = self._datasets()
        portraits = self._portraits()
        latest_run = training_runs[0] if training_runs else None
        latest_version = versions[0] if versions else None
        latest_dataset = datasets[0] if datasets else None
        latest_portrait = (
            self._portrait_stats(portraits[0]) if portraits else None
        )
        return (
            VersionNodeView(
                "base",
                0,
                "Base · "
                f"{getattr(latest_run, 'base_model', '—') if latest_run else '—'}",
                "Исходная точка lineage.",
                "source",
                "good" if latest_run else "pending",
                "main",
            ),
            VersionNodeView(
                "dataset",
                1,
                "Dataset · "
                f"{getattr(latest_run, 'dataset_version', '') or getattr(latest_dataset, 'title', '—')}",
                self._dataset_note(),
                (
                    getattr(latest_dataset, "status", "ожидание")
                    if latest_dataset
                    else "ожидание"
                ),
                (
                    "good"
                    if latest_dataset
                    and getattr(latest_dataset, "status", "")
                    == "Одобрен для обучения"
                    else "pending"
                ),
                "main",
            ),
            VersionNodeView(
                "training",
                2,
                f"Train · {getattr(latest_run, 'run_id', '—')}",
                (
                    getattr(
                        latest_run,
                        "title",
                        "training run пока не создан",
                    )
                    if latest_run
                    else "training run пока не создан"
                ),
                (
                    getattr(latest_run, "status", "ожидание")
                    if latest_run
                    else "ожидание"
                ),
                (
                    "good"
                    if latest_run and getattr(latest_run, "artifact_path", "")
                    else "pending"
                ),
                "main",
            ),
            VersionNodeView(
                "snapshot",
                3,
                f"Version · {getattr(latest_version, 'version_id', '—')}",
                (
                    getattr(
                        latest_version,
                        "title",
                        "snapshot пока не создан",
                    )
                    if latest_version
                    else "snapshot пока не создан"
                ),
                (
                    getattr(latest_version, "status", "ожидание")
                    if latest_version
                    else "ожидание"
                ),
                "good" if latest_version else "pending",
                "current",
            ),
            VersionNodeView(
                "portrait",
                4,
                "Portrait · "
                f"{latest_portrait.title if latest_portrait else '—'}",
                self._portrait_note(latest_portrait),
                (
                    "готов"
                    if latest_portrait and latest_portrait.failures == 0
                    else "ожидание"
                ),
                (
                    "good"
                    if latest_portrait and latest_portrait.failures == 0
                    else "pending"
                ),
                "main",
            ),
            VersionNodeView(
                "delta",
                5,
                "Delta · latest - previous",
                self.delta_line() or "нужны два портретных запуска",
                "готов" if len(portraits) >= 2 else "ожидание",
                "good" if len(portraits) >= 2 else "pending",
                "main",
            ),
        )

    def _portrait_note(self, latest: PortraitStats | None) -> str:
        if latest is None:
            return "Портрет не собран."
        score_line = self._score_line(latest.scores) or "нет score"
        return (
            f"{latest.passed}/{latest.total} valid · ошибок {latest.failures} · "
            f"{score_line}"
        )


__all__ = ("AgentsViewModel",)
