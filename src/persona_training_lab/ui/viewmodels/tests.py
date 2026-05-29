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
    title: str = "Тесты"
    subtitle: str = "Запустите smoke-проверку локальной модели."
    setup_rows: tuple[tuple[str, str], ...] = (
        ("Цель", "Проверка ответа локальной модели"),
        ("Режим", "smoke inference pack"),
        ("Снимок", "последний зарегистрированный, если есть"),
        ("Оценка", "структурная: ответ получен / ошибка"),
    )
    metrics: tuple[EvaluationMetric, ...] = (
        EvaluationMetric("Запусков", "0", "тесты пока не запускались"),
        EvaluationMetric("Последний статус", "—", "нет результата"),
        EvaluationMetric("Ответы", "—", "нет результата"),
        EvaluationMetric("Ошибки", "—", "нет результата"),
    )
    problematic_cases: tuple[EvaluationCase, ...] = (
        EvaluationCase("Тесты пока не запускались", "Нажмите «Запустить проверку», чтобы получить реальные ответы модели."),
    )
    context_rows: tuple[str, ...] = (
        "Smoke-проверка не оценивает смысл ответа",
        "Цель: убедиться, что модель загружается и отвечает",
    )
    run_in_progress: bool = False

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self._apply_tests_connector()

    def _apply_tests_connector(self) -> None:
        if self.experiments_service is None:
            self.title = "Тесты"
            self.subtitle = "Сервис тестов не подключён"
            self.problematic_cases = (EvaluationCase("Сервис тестов не подключён", "Проверьте wiring приложения."),)
            return
        try:
            scenarios = self.experiments_service.list_experiments()
        except Exception:
            self.title = "Тесты"
            self.subtitle = "Не удалось загрузить тесты"
            self.problematic_cases = (EvaluationCase("Не удалось загрузить тесты", "Проверьте подключение к базе данных."),)
            self.context_rows = ("Проверка устойчивости, поведения и сохранения характера",)
            return

        if not scenarios:
            self.title = "Тесты"
            self.subtitle = "Тесты пока не запускались"
            self.metrics = (
                EvaluationMetric("Запусков", "0", "тесты пока не запускались"),
                EvaluationMetric("Последний статус", "—", "нет результата"),
                EvaluationMetric("Ответы", "—", "нет результата"),
                EvaluationMetric("Ошибки", "—", "нет результата"),
            )
            self.problematic_cases = (
                EvaluationCase("Тесты пока не запускались", "Нажмите «Запустить проверку», чтобы получить реальные ответы модели."),
            )
            self.context_rows = (
                "Smoke-проверка локальной модели",
                "Проверяется факт загрузки и генерации ответа",
                "Смысл ответа разбирается вручную позже",
            )
            return

        latest = scenarios[0]
        lines = [line for line in latest.subtitle.splitlines() if line.strip()]
        summary = lines[0] if lines else latest.subtitle
        answer_lines = lines[1:] if len(lines) > 1 else (latest.subtitle,)
        failures = 0 if latest.status == "Пройден" else 1
        self.title = f"Тесты · {latest.title}"
        self.subtitle = summary
        self.metrics = (
            EvaluationMetric("Запусков", str(len(scenarios)), "сохранённые smoke test runs"),
            EvaluationMetric("Последний статус", latest.status, "последний сохранённый запуск"),
            EvaluationMetric("Ответы", summary.split(" ")[0] if summary else "—", "получено ответов"),
            EvaluationMetric("Ошибки", str(failures), "структурные ошибки запуска"),
        )
        self.problematic_cases = tuple(
            EvaluationCase(f"Ответ {idx + 1}", line)
            for idx, line in enumerate(answer_lines[:12])
        ) or (EvaluationCase("Ответы не сохранены", "Запустите проверку ещё раз."),)
        self.context_rows = (
            f"Последний тест · {latest.experiment_id}",
            f"Статус · {latest.status}",
            "Smoke pack · 3 промпта",
            "Оценка смысла не выполняется автоматически",
        )

    def begin_run(self) -> bool:
        if self.run_in_progress:
            return False
        self.run_in_progress = True
        self.subtitle = "Проверка модели выполняется…"
        return True

    def run_tests_sync(self) -> tuple[bool, str]:
        if self.experiments_service is None:
            return False, "Сервис тестов не подключён"
        result = self.experiments_service.run_smoke_test_pack()
        return result.ok, result.message

    def finish_run(self, _ok: bool, message: str) -> None:
        self.run_in_progress = False
        self.refresh()
        self.subtitle = message
