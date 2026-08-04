from __future__ import annotations

from persona_training_lab.ui.viewmodels.analysis import (
    AnalysisViewModel as _AnalysisViewModel,
    CompareMetric,
    CompareSample,
    CompareSummary,
)


class AnalysisViewModel(_AnalysisViewModel):
    """Exact version-to-version analysis selected from the lineage tree."""

    def __init__(self, *args, **kwargs) -> None:
        self.selected_model_version_id = ""
        self.current_model_version_id = ""
        self.selected_node_id = ""
        self.current_node_id = ""
        super().__init__(*args, **kwargs)

    def set_lineage_context(self, payload: dict[str, object]) -> None:
        selected_raw = payload.get("selected", payload)
        current_raw = payload.get("current", {})
        selected = selected_raw if isinstance(selected_raw, dict) else {}
        current = current_raw if isinstance(current_raw, dict) else {}
        self.selected_model_version_id = str(
            selected.get("model_version_id", "") or ""
        )
        self.current_model_version_id = str(
            current.get("model_version_id", "") or ""
        )
        self.selected_node_id = str(
            selected.get("node_id", "") or ""
        )
        self.current_node_id = str(current.get("node_id", "") or "")
        self.refresh()

    def refresh(self) -> None:
        selected_id = getattr(self, "selected_model_version_id", "")
        current_id = getattr(self, "current_model_version_id", "")
        if not selected_id or not current_id:
            super().refresh()
            return

        service = self.experiments_service
        if service is None:
            self._set_missing_pair(
                selected_id,
                current_id,
                "Сервис тестов не подключён",
            )
            return
        try:
            experiments = service.list_experiments()
        except Exception:
            self._set_missing_pair(
                selected_id,
                current_id,
                "Не удалось загрузить сохранённые тесты",
            )
            return

        selected_experiment = self._experiment_for_version(
            experiments,
            selected_id,
        )
        current_experiment = self._experiment_for_version(
            experiments,
            current_id,
        )
        missing: list[str] = []
        if selected_experiment is None:
            missing.append(selected_id)
        if current_experiment is None:
            missing.append(current_id)
        if missing:
            self._set_missing_pair(
                selected_id,
                current_id,
                "Нет портрета для: " + ", ".join(dict.fromkeys(missing)),
            )
            return

        # Base view-model renders previous on the left and latest on the right.
        # Passing selected as previous and current as latest gives the exact pair
        # requested from the tree, independent of experiment creation order.
        self._apply_experiment(current_experiment, selected_experiment)
        self.title = f"Анализ · {selected_id} ↔ {current_id}"
        self.subtitle = (
            "Точное сравнение версий из lineage. Левый портрет относится к "
            f"{selected_id}, правый — к {current_id}."
        )

    @staticmethod
    def _experiment_for_version(experiments, version_id: str):
        marker = f"model_version={version_id}"
        return next(
            (
                experiment
                for experiment in experiments
                if marker in getattr(experiment, "subtitle", "")
            ),
            None,
        )

    def _set_missing_pair(
        self,
        selected_id: str,
        current_id: str,
        reason: str,
    ) -> None:
        self.title = f"Анализ · {selected_id} ↔ {current_id}"
        self.subtitle = (
            f"{reason}. Система не подменяет отсутствующий результат портретом "
            "другой модели."
        )
        self.left = CompareSummary(
            "Выбранная версия",
            selected_id,
            "—",
            "портрет отсутствует",
            "—",
        )
        self.right = CompareSummary(
            "Актуальная версия",
            current_id,
            "—",
            "портрет отсутствует",
            "—",
        )
        self.metrics = (
            CompareMetric(
                "Big Five KPI",
                "—",
                "нужны портреты обеих версий",
            ),
            CompareMetric(
                "Дельта",
                "—",
                "сравнение не вычисляется на неполной паре",
            ),
            CompareMetric(
                "Ошибки",
                "—",
                reason,
            ),
        )
        self.insights = (
            "Запустите портрет из карточки каждой версии дерева.",
            "Батарея и scoring должны совпадать для научного сравнения.",
            "После появления обоих результатов эта вкладка выберет их по model_version_id.",
        )
        self.deltas = (
            "Никакие данные другой версии не подставлены автоматически.",
        )
        self.samples = (
            CompareSample(
                "Сравнение ожидает данные",
                selected_id,
                current_id,
            ),
        )
