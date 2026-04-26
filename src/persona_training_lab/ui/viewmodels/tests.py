from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.experiments.service import ExperimentsService


@dataclass(slots=True, frozen=True)
class EvaluationMetric:
    title: str
    value: str
    note: str


@dataclass(slots=True, frozen=True)
class EvaluationCase:
    title: str
    note: str


@dataclass(slots=True)
class TestsViewModel:
    __test__ = False

    experiments_service: ExperimentsService | None = None
    title: str = "Тесты · evr_psychotype_pack_04"
    subtitle: str = "Независимая проверка snapshot после freeze и до выводов."
    setup_rows: tuple[tuple[str, str], ...] = (
        ("Снимок", "snp_mia_v3_candidate"),
        ("Тест-пак", "psychotype_pack_04"),
        ("Режим", "batched response collection"),
        ("Покрытие", "traits · contradiction · stress"),
    )
    metrics: tuple[EvaluationMetric, ...] = (
        EvaluationMetric("Совпадение профиля", "0.87", "близко к целевому профилю"),
        EvaluationMetric("Стабильность", "0.81", "хорошо держится под перефразами"),
        EvaluationMetric("Согласованность", "0.79", "ядро держится без сильных провалов"),
        EvaluationMetric("Противоречия", "0.11", "низко, но есть кейсы на ручной просмотр"),
    )
    problematic_cases: tuple[EvaluationCase, ...] = (
        EvaluationCase("Кейс #14", "под моральным давлением ответ сместился в мягкость вместо твёрдой границы"),
        EvaluationCase("Кейс #22", "тепло осталось высоким, но boundary-setting стало слишком мягким"),
        EvaluationCase("Кейс #31", "обнаружено одно противоречие между парой перефразированных сценариев"),
    )
    context_rows: tuple[str, ...] = (
        "Статус снимка · протестирован",
        "Тип пакета · psychotype + stress",
        "Сбор ответов · завершён",
        "Режим review · доступен",
    )

    def __post_init__(self) -> None:
        self._apply_tests_connector()

    def _apply_tests_connector(self) -> None:
        if self.experiments_service is None:
            return
        try:
            scenarios = self.experiments_service.list_experiments()
        except Exception:
            self.title = "Тесты"
            self.subtitle = "Не удалось загрузить тесты"
            self.problematic_cases = (
                EvaluationCase("Не удалось загрузить тесты", "Проверьте подключение к базе данных."),
            )
            self.context_rows = (
                "Проверка устойчивости, поведения и сохранения характера",
            )
            return

        if not scenarios:
            self.title = "Тесты"
            self.subtitle = "Тесты пока не созданы"
            self.problematic_cases = (
                EvaluationCase("Тесты пока не созданы", "Сценарии проверки личности появятся после добавления записей."),
            )
            self.context_rows = (
                "Сценарии проверки личности",
                "Проверка устойчивости, поведения и сохранения характера",
            )
            return

        self.title = f"Тесты · {scenarios[0].title}"
        self.subtitle = "Сценарии проверки личности"
        self.problematic_cases = tuple(
            EvaluationCase(item.title, item.subtitle)
            for item in scenarios
        )
        self.context_rows = (
            "Сценарии проверки личности",
            "Проверка устойчивости, поведения и сохранения характера",
        )
