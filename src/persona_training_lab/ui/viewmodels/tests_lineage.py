from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.viewmodels.tests import (
    EvaluationCase,
    EvaluationMetric,
    TestsViewModel as _TestsViewModel,
)


class TestsViewModel(_TestsViewModel):
    """Portrait workflow scoped to the exact model selected in lineage."""

    def _latest_for_target(self, scenarios):
        if not self.target_model_version_id:
            return scenarios[0]
        marker = f"model_version={self.target_model_version_id}"
        match = next(
            (
                scenario
                for scenario in scenarios
                if marker in scenario.subtitle
            ),
            None,
        )
        if match is not None:
            return match
        return SimpleNamespace(
            experiment_id="",
            title=f"{self.target_model_version_id} · портрет не собран",
            subtitle=(
                "PORTRAIT: 0/0 Big Five items · "
                f"model_version={self.target_model_version_id} · "
                f"artifact={self.target_artifact_path or '—'}"
            ),
            status="Не запускался",
        )

    def _apply_tests_connector(self) -> None:
        super()._apply_tests_connector()
        version_id = self.target_model_version_id
        service = self.experiments_service
        if not version_id or service is None:
            return
        try:
            scenarios = service.list_experiments()
        except Exception:
            return
        marker = f"model_version={version_id}"
        matching = [
            scenario
            for scenario in scenarios
            if marker in scenario.subtitle
        ]
        if matching:
            self.metrics = (
                EvaluationMetric(
                    "Запусков версии",
                    str(len(matching)),
                    f"портреты, связанные с {version_id}",
                ),
                *self.metrics[1:],
            )
            return

        self.title = f"Тесты · {version_id}"
        self.subtitle = (
            "Для выбранной версии портрет ещё не собран. Другие сохранённые "
            "результаты намеренно не подставляются."
        )
        self.metrics = (
            EvaluationMetric(
                "Запусков версии",
                "0",
                f"для {version_id} нет сохранённых portrait runs",
            ),
            EvaluationMetric(
                "Последний статус",
                "—",
                "тест выбранных весов ещё не запускался",
            ),
            EvaluationMetric("Пункты", "—", "нет результата"),
            EvaluationMetric("Ошибки", "—", "нет результата"),
        )
        self.problematic_cases = (
            EvaluationCase(
                "Портрет выбранной версии не собран",
                (
                    f"Нажмите «Собрать портрет»: тест будет запущен на весах "
                    f"{version_id}, а не на последней модели по умолчанию."
                ),
            ),
        )
