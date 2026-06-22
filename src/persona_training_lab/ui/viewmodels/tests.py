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
    subtitle: str = "Соберите психологический портрет текущей модели."
    setup_rows: tuple[tuple[str, str], ...] = (
        ("Цель", "Психологический портрет модели"),
        ("Режим", "neutral portrait questions"),
        ("Снимок", "последний зарегистрированный, если есть"),
        ("Оценка", "наблюдение + ручной разбор ответов"),
    )
    metrics: tuple[EvaluationMetric, ...] = (
        EvaluationMetric("Запусков", "0", "портреты пока не собирались"),
        EvaluationMetric("Последний статус", "—", "нет результата"),
        EvaluationMetric("Измерения", "—", "нет результата"),
        EvaluationMetric("Ошибки", "—", "нет результата"),
    )
    problematic_cases: tuple[EvaluationCase, ...] = (
        EvaluationCase("Портрет пока не собран", "Нажмите «Собрать портрет», чтобы получить реальные ответы модели."),
    )
    context_rows: tuple[str, ...] = (
        "Тесты собирают психологический портрет модели, а не медицинскую диагностику",
        "Вопросы нейтральные: они не подсказывают желаемый характер ответа",
        "Формат ограничен краткостью, чтобы модель не уходила в воду",
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
            self.context_rows = ("Психологический портрет модели",)
            return

        if not scenarios:
            self.title = "Тесты"
            self.subtitle = "Психологический портрет пока не собран"
            self.metrics = (
                EvaluationMetric("Запусков", "0", "портреты пока не собирались"),
                EvaluationMetric("Последний статус", "—", "нет результата"),
                EvaluationMetric("Измерения", "—", "нет результата"),
                EvaluationMetric("Ошибки", "—", "нет результата"),
            )
            self.problematic_cases = (
                EvaluationCase("Портрет пока не собран", "Нажмите «Собрать портрет», чтобы получить реальные ответы модели."),
            )
            self.context_rows = (
                "Neutral personality portrait pack",
                "Измерения: самоописание, раздражение, несогласие, неуверенность, сбой понимания, границы, инициатива",
                "Автооценка смысла не выполняется: ответы размечаются вручную",
            )
            return

        latest = scenarios[0]
        summary, cases = self._parse_subtitle(latest.subtitle)
        failures = 0 if latest.status in {"Портрет собран", "Пройден"} else 1
        answers_value = self._answers_value(summary)
        self.title = f"Тесты · {latest.title}"
        self.subtitle = summary or latest.subtitle
        self.metrics = (
            EvaluationMetric("Запусков", str(len(scenarios)), "сохранённые portrait/test runs"),
            EvaluationMetric("Последний статус", latest.status, "последний сохранённый запуск"),
            EvaluationMetric("Измерения", answers_value, "получено портретных ответов"),
            EvaluationMetric("Ошибки", str(failures), "структурные ошибки запуска"),
        )
        self.problematic_cases = cases or (EvaluationCase("Ответы не сохранены", "Запустите сбор портрета ещё раз."),)
        self.context_rows = (
            f"Последний портрет · {latest.experiment_id}",
            f"Статус · {latest.status}",
            "Portrait pack · нейтральные вопросы",
            "Смысл и устойчивость оцениваются ручной разметкой ответов",
        )

    def _answers_value(self, summary: str) -> str:
        if not summary:
            return "—"
        head = summary.split(" · ")[0]
        return head.replace("PORTRAIT: ", "").replace("SUMMARY: ", "")

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
            case_title = lines[0].replace("CASE ", "Кейс ")
            dimension = next((line.removeprefix("DIMENSION: ").strip() for line in lines if line.startswith("DIMENSION: ")), "")
            question = next((line.removeprefix("QUESTION: ").strip() for line in lines if line.startswith("QUESTION: ")), "")
            prompt = next((line.removeprefix("PROMPT: ").strip() for line in lines if line.startswith("PROMPT: ")), "")
            status = next((line.removeprefix("STATUS: ").strip() for line in lines if line.startswith("STATUS: ")), "")
            response = next((line.removeprefix("RESPONSE: ").strip() for line in lines if line.startswith("RESPONSE: ")), "")
            note_parts = []
            if dimension:
                note_parts.append(f"Измерение: {dimension}")
            if question:
                note_parts.append(f"Вопрос: {question}")
            elif prompt:
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
        self.subtitle = "Сбор психологического портрета выполняется…"
        return True

    def run_tests_sync(self) -> tuple[bool, str]:
        if self.experiments_service is None:
            return False, "Сервис тестов не подключён"
        result = self.experiments_service.run_personality_portrait_test_pack()
        return result.ok, result.message

    def finish_run(self, _ok: bool, message: str) -> None:
        self.run_in_progress = False
        self.refresh()
        self.subtitle = message

    def review_text(self) -> str:
        lines = [self.subtitle, ""]
        for case in self.problematic_cases:
            lines.append(case.title)
            lines.append(case.note)
            lines.append("")
        return "\n".join(lines).strip()
