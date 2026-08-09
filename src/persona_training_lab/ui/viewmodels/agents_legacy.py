from __future__ import annotations

from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentDetailView,
    PortraitStats,
    VersionNodeView,
)
from persona_training_lab.ui.viewmodels.agents_guidance import (
    AgentsGuidanceViewModel,
)


class AgentsViewModel(AgentsGuidanceViewModel):
    """Compatibility VM retaining the pre-atomic graph and detail projection."""

    __slots__ = ()

    def selected_detail(self) -> AgentDetailView:
        return self.node_detail("snapshot")

    def node_detail(self, node_id: str) -> AgentDetailView:
        datasets = self._datasets()
        runs = self._training_runs()
        portraits = self._portraits()
        latest_dataset = datasets[0] if datasets else None
        latest_run = runs[0] if runs else None
        latest_portrait = self._portrait_stats(portraits[0]) if portraits else None

        if node_id == "base":
            return AgentDetailView(
                "Base model",
                "\n".join(
                    (
                        "Модель: "
                        f"{getattr(latest_run, 'base_model', '—') if latest_run else '—'}",
                        "Роль: исходная точка lineage.",
                        "Следующий узел: dataset.",
                    )
                ),
                (
                    "Проверить локальные файлы модели",
                    "Не смешивать разные base model в одном сравнении",
                    "Фиксировать модель в протоколе",
                ),
                (
                    "Проверить локальную модель",
                    "Перейти к датасету",
                ),
            )
        if node_id == "dataset":
            return AgentDetailView(
                "Dataset",
                "\n".join(
                    (
                        f"Название: {getattr(latest_dataset, 'title', '—')}",
                        f"Статус: {getattr(latest_dataset, 'status', 'ожидание')}",
                        f"Записей: {getattr(latest_dataset, 'record_count', '—')}",
                        f"Валидных: {getattr(latest_dataset, 'valid_count', '—')}",
                        f"Ошибок: {getattr(latest_dataset, 'invalid_count', '—')}",
                    )
                ),
                (
                    "Структура JSONL валидна",
                    "Датасет одобрен автором",
                    "Смысл данных проверен вручную",
                ),
                (
                    "Проверить датасет",
                    "Одобрить для обучения",
                    "Создать training run",
                ),
            )
        if node_id == "training":
            return AgentDetailView(
                "Training run",
                "\n".join(
                    (
                        f"Run: {getattr(latest_run, 'run_id', '—')}",
                        f"Название: {getattr(latest_run, 'title', '—')}",
                        f"Статус: {getattr(latest_run, 'status', 'ожидание')}",
                        f"Epoch: {getattr(latest_run, 'epoch_progress', '—')}",
                        f"Loss: {getattr(latest_run, 'loss', '—')}",
                        "Artifact: "
                        f"{getattr(latest_run, 'artifact_path', '—') or '—'}",
                    )
                ),
                (
                    "Запуск завершён",
                    "Artifact path не пустой",
                    "Логи доступны",
                    "UI не зависал во время обучения",
                ),
                (
                    "Открыть логи",
                    "Создать snapshot из artifact",
                    "Повторить запуск при ошибке",
                ),
            )
        if node_id == "snapshot":
            return AgentDetailView(
                "Model version",
                self._current_version_body(latest_portrait),
                (
                    "Snapshot зарегистрирован",
                    "Artifact path существует",
                    "Понятно, от какого training run он создан",
                    "Перед откатом есть текущий портрет",
                ),
                (
                    "Сделать актуальной",
                    "Сравнить с текущей",
                    "Запустить портрет",
                    "Пометить неудачной",
                    "Откатиться к этой точке",
                ),
            )
        if node_id == "portrait":
            return AgentDetailView(
                "Personality portrait",
                "\n".join(
                    (
                        "Портрет: "
                        f"{latest_portrait.title if latest_portrait else '—'}",
                        "VALID: "
                        f"{latest_portrait.passed if latest_portrait else 0}/"
                        f"{latest_portrait.total if latest_portrait else 0}",
                        "Ошибок: "
                        f"{latest_portrait.failures if latest_portrait else '—'}",
                        "Big Five KPI: "
                        f"{self._score_line(latest_portrait.scores) if latest_portrait else '—'}",
                    )
                ),
                (
                    "Все пункты имеют VALID_SCORE",
                    "KPI построен",
                    "Батарея и scoring зафиксированы",
                ),
                (
                    "Повторить портрет",
                    "Открыть анализ",
                    "Экспортировать raw responses",
                ),
            )
        if node_id == "delta":
            return AgentDetailView(
                "Analysis delta",
                "\n".join(
                    (
                        f"Delta: {self.delta_line() or 'нужен второй портрет'}",
                        "Latest: "
                        f"{getattr(portraits[0], 'title', '—') if portraits else '—'}",
                        "Previous: "
                        f"{getattr(portraits[1], 'title', '—') if len(portraits) > 1 else '—'}",
                    )
                ),
                (
                    "Есть два портрета",
                    "Одинаковая батарея",
                    "Одинаковые scoring rules",
                    "Сравнение latest - previous",
                ),
                (
                    "Открыть анализ",
                    "Собрать следующий портрет",
                    "Сделать заметку в протокол",
                ),
            )
        return self.node_detail("snapshot")

    def _current_version_body(self, latest: PortraitStats | None) -> str:
        versions = self._model_versions()
        version = versions[0] if versions else None
        if version is None:
            return (
                "Snapshot пока не создан. Сначала доведите обучение до artifact "
                "и зарегистрируйте версию."
            )
        score_line = (
            self._score_line(latest.scores) if latest else "портрет не собран"
        )
        return "\n".join(
            (
                f"Версия: {version.title}",
                f"Статус: {version.status}",
                f"Artifact: {version.artifact_path or '—'}",
                f"Big Five KPI: {score_line}",
                f"Delta: {self.delta_line() or 'нужен второй портрет'}",
            )
        )

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
