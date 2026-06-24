from __future__ import annotations

from dataclasses import dataclass
import re

from persona_training_lab.application.experiments.service import ExperimentsService


CASE_HEADER_RE = re.compile(r"(?m)^CASE\s+\d+")


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
        ("Цель", "Big Five KPI портрет модели"),
        ("Режим", "scored self-report items"),
        ("Снимок", "последний зарегистрированный, если есть"),
        ("Ответ", "только SCORE: 1-5"),
    )
    metrics: tuple[EvaluationMetric, ...] = (
        EvaluationMetric("Запусков", "0", "портреты пока не собирались"),
        EvaluationMetric("Последний статус", "—", "нет результата"),
        EvaluationMetric("Пункты", "—", "нет результата"),
        EvaluationMetric("Ошибки", "—", "нет результата"),
    )
    problematic_cases: tuple[EvaluationCase, ...] = (
        EvaluationCase("Портрет пока не собран", "Нажмите «Собрать портрет», чтобы получить SCORE-ответы модели."),
    )
    context_rows: tuple[str, ...] = (
        "Основа: Big Five/IPIP-style шкала",
        "Каждый пункт даёт KPI 1-5, а не длинный текст",
        "Это исследовательская метрика модели, не клиническая диагностика человека",
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
            self.context_rows = ("Big Five KPI портрет модели",)
            return

        if not scenarios:
            self.title = "Тесты"
            self.subtitle = "Психологический портрет пока не собран"
            self.metrics = (
                EvaluationMetric("Запусков", "0", "портреты пока не собирались"),
                EvaluationMetric("Последний статус", "—", "нет результата"),
                EvaluationMetric("Пункты", "—", "нет результата"),
                EvaluationMetric("Ошибки", "—", "нет результата"),
            )
            self.problematic_cases = (
                EvaluationCase("Портрет пока не собран", "Нажмите «Собрать портрет», чтобы получить SCORE-ответы модели."),
            )
            self.context_rows = (
                "Big Five/IPIP-style scored pack",
                "Факторы: Extraversion, Agreeableness, Conscientiousness, Emotional Stability, Openness",
                "Дальше анализ считает средние KPI по факторам",
            )
            return

        latest = scenarios[0]
        summary, cases = self._parse_subtitle(latest.subtitle)
        invalid_count = sum(1 for case in cases if "Валидность: нет" in case.note)
        failures = invalid_count if latest.status in {"Портрет собран", "Пройден"} else max(1, invalid_count)
        answers_value = self._answers_value(summary)
        self.title = f"Тесты · {latest.title}"
        self.subtitle = summary or latest.subtitle
        self.metrics = (
            EvaluationMetric("Запусков", str(len(scenarios)), "сохранённые portrait/test runs"),
            EvaluationMetric("Последний статус", latest.status, "последний сохранённый запуск"),
            EvaluationMetric("Пункты", answers_value, "валидные SCORE-ответы"),
            EvaluationMetric("Ошибки", str(failures), "пункты без валидного SCORE"),
        )
        self.problematic_cases = cases or (EvaluationCase("Ответы не сохранены", "Запустите сбор портрета ещё раз."),)
        self.context_rows = (
            f"Последний портрет · {latest.experiment_id}",
            f"Статус · {latest.status}",
            "Big Five scored items",
            "KPI: средние баллы по факторам с reverse scoring",
        )

    def _answers_value(self, summary: str) -> str:
        if not summary:
            return "—"
        head = summary.split(" · ")[0]
        return head.replace("PORTRAIT: ", "").replace("SUMMARY: ", "")

    def _split_case_records(self, subtitle: str) -> tuple[str, list[str]]:
        match = CASE_HEADER_RE.search(subtitle)
        if match is None:
            return subtitle.strip(), []
        summary = subtitle[: match.start()].strip()
        records = [record.strip() for record in CASE_HEADER_RE.split(subtitle[match.start():]) if record.strip()]
        headers = CASE_HEADER_RE.findall(subtitle[match.start():])
        return summary, [f"{header}\n{record}" for header, record in zip(headers, records, strict=False)]

    def _parse_subtitle(self, subtitle: str) -> tuple[str, tuple[EvaluationCase, ...]]:
        summary, blocks = self._split_case_records(subtitle)
        if not summary and not blocks:
            return subtitle, ()
        cases: list[EvaluationCase] = []
        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            case_title = lines[0].replace("CASE ", "Пункт ")
            trait = next((line.removeprefix("TRAIT: ").strip() for line in lines if line.startswith("TRAIT: ")), "")
            key = next((line.removeprefix("KEY: ").strip() for line in lines if line.startswith("KEY: ")), "")
            reverse = next((line.removeprefix("REVERSE: ").strip() for line in lines if line.startswith("REVERSE: ")), "")
            item = next((line.removeprefix("ITEM: ").strip() for line in lines if line.startswith("ITEM: ")), "")
            status = next((line.removeprefix("STATUS: ").strip() for line in lines if line.startswith("STATUS: ")), "")
            valid_score = next((line.removeprefix("VALID_SCORE: ").strip() for line in lines if line.startswith("VALID_SCORE: ")), "")
            raw_response = next((line.removeprefix("RAW_RESPONSE: ").strip() for line in lines if line.startswith("RAW_RESPONSE: ")), "")
            response = next((line.removeprefix("RESPONSE: ").strip() for line in lines if line.startswith("RESPONSE: ")), "")
            note_parts = []
            if trait:
                note_parts.append(f"Фактор: {trait}")
            if key:
                note_parts.append(f"Ключ: {key} · reverse={reverse or '0'}")
            if item:
                note_parts.append(f"Пункт: {item}")
            if status:
                note_parts.append(f"Статус: {status}")
            if valid_score:
                note_parts.append(f"Валидность: {'да' if valid_score == '1' else 'нет'}")
            if response:
                note_parts.append(f"Ответ: {response}")
            if raw_response and raw_response != response:
                note_parts.append(f"Сырой ответ: {raw_response}")
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
