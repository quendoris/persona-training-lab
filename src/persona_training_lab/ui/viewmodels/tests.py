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
            self.context_rows = ("Smoke-проверка локальной модели",)
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
        summary, cases = self._parse_subtitle(latest.subtitle)
        failures = 0 if latest.status == "Пройден" else 1
        answers_value = summary.split(" · ")[0].replace("SUMMARY: ", "") if summary else "—"
        self.title = f"Тесты · {latest.title}"
        self.subtitle = summary or latest.subtitle
        self.metrics = (
            EvaluationMetric("Запусков", str(len(scenarios)), "сохранённые smoke test runs"),
            EvaluationMetric("Последний статус", latest.status, "последний сохранённый запуск"),
            EvaluationMetric("Ответы", answers_value, "получено ответов"),
            EvaluationMetric("Ошибки", str(failures), "структурные ошибки запуска"),
        )
        self.problematic_cases = cases or (EvaluationCase("Ответы не сохранены", "Запустите проверку ещё раз."),)
        self.context_rows = (
            f"Последний тест · {latest.experiment_id}",
            f"Статус · {latest.status}",
            "Smoke pack · 3 промпта",
            "Оценка смысла не выполняется автоматически",
        )

    def _parse_subtitle(self, subtitle: str) -> tuple[str, tuple[EvaluationCase, ...]]:
        blocks = [block.strip() for block in subtitle.split("\n\n") if block.strip()]
        if not blocks:
            return subtitle, ()
        summary = blocks[0]
        cases: list[EvaluationCase] = []
        for block in blocks[1:]:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            case_title = lines[0].replace("CASE ", "Ответ ")
            prompt = next((line.removeprefix("PROMPT: ").strip() for line in lines if line.startswith("PROMPT: ")), "")
            status = next((line.removeprefix("STATUS: ").strip() for line in lines if line.startswith("STATUS: ")), "")
            response = next((line.removeprefix("RESPONSE: ").strip() for line in lines if line.startswith("RESPONSE: ")), "")
            note_parts = []
            if prompt:
                note_parts.append(f"Промпт: {prompt}")
            if status:
                note_parts.append(f"Статус: {status}")
            if response:
                note_parts.append(f"Ответ: {response}")
            cases.append(EvaluationCase(case_title, "\n".join(note_parts) if note_parts else block))
        if cases:
            return summary, tuple(cases)

        legacy_lines = [line for line in subtitle.splitlines() if line.strip()]
        legacy_summary = legacy_lines[0] if legacy_lines else subtitle
        legacy_cases = tuple(EvaluationCase(f"Ответ {idx + 1}", line) for idx, line in enumerate(legacy_lines[1:12]))
        return legacy_summary, legacy_cases

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
