from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.analysis.service import AnalysisService
from persona_training_lab.application.experiments.service import ExperimentsService


@dataclass(slots=True, frozen=True)
class CompareMetric:
    title: str
    delta: str
    note: str


@dataclass(slots=True, frozen=True)
class CompareSummary:
    title: str
    subtitle: str
    profile_match: str
    stability: str
    contradiction: str


@dataclass(slots=True, frozen=True)
class CompareSample:
    title: str
    left_note: str
    right_note: str


@dataclass(slots=True)
class AnalysisViewModel:
    analysis_service: AnalysisService | None = None
    experiments_service: ExperimentsService | None = None
    title: str = "Анализ"
    subtitle: str = "Результаты анализа пока не созданы"
    left: CompareSummary = CompareSummary(
        title="нет данных",
        subtitle="ожидание результатов тестов",
        profile_match="—",
        stability="—",
        contradiction="—",
    )
    right: CompareSummary = CompareSummary(
        title="последний smoke run",
        subtitle="ожидание результатов тестов",
        profile_match="—",
        stability="—",
        contradiction="—",
    )
    metrics: tuple[CompareMetric, ...] = (
        CompareMetric("Ответы модели", "—", "Тесты пока не запускались"),
        CompareMetric("Статус запуска", "—", "Тесты пока не запускались"),
        CompareMetric("Ошибки", "—", "Тесты пока не запускались"),
    )
    insights: tuple[str, ...] = (
        "Результаты анализа пока не созданы",
    )
    deltas: tuple[str, ...] = (
        "Запустите smoke-проверку во вкладке «Тесты», затем обновите анализ.",
    )
    samples: tuple[CompareSample, ...] = (
        CompareSample(
            "Ожидание результатов",
            "Тесты пока не запускались",
            "Ответы модели пока не сохранены",
        ),
    )

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        if self._apply_experiments_connector():
            return
        self._apply_analysis_connector()

    def _apply_experiments_connector(self) -> bool:
        if self.experiments_service is None:
            return False
        try:
            experiments = self.experiments_service.list_experiments()
        except Exception:
            self.title = "Анализ"
            self.subtitle = "Не удалось загрузить результаты тестов"
            self.insights = ("Не удалось загрузить результаты тестов",)
            self.deltas = ("Проверьте SQLite-реестр experiments и повторите обновление анализа.",)
            self.samples = (CompareSample("Ошибка загрузки", "experiments", "Не удалось прочитать результаты тестов"),)
            return True
        if not experiments:
            self.title = "Анализ"
            self.subtitle = "Нет результатов тестов для анализа"
            self.left = CompareSummary("Ожидание", "нет сохранённых test runs", "—", "—", "—")
            self.right = CompareSummary("Smoke run", "ещё не запускался", "—", "—", "—")
            self.metrics = (
                CompareMetric("Ответы модели", "0/0", "Нет сохранённых smoke test runs"),
                CompareMetric("Статус запуска", "—", "Запустите проверку во вкладке «Тесты»"),
                CompareMetric("Ошибки", "—", "Нет данных"),
            )
            self.insights = (
                "Анализ ждёт реальные результаты из вкладки «Тесты».",
                "Сейчас выводы не строятся, чтобы не показывать декоративные метрики.",
                "Сначала нужно получить хотя бы один smoke run локальной модели.",
            )
            self.deltas = (
                "Следующий шаг: открыть «Тесты» и нажать «Запустить проверку».",
                "После сохранения результата вернитесь сюда и обновите вкладку/перезапустите приложение.",
                "Смысл ответов пока оценивается вручную; автологика анализирует только статус и наличие ответов.",
            )
            self.samples = (CompareSample("Нет кейсов", "—", "Нет сохранённых ответов модели"),)
            return True

        latest = experiments[0]
        summary, cases = self._parse_experiment_subtitle(latest.subtitle)
        passed, total = self._parse_passed_total(summary)
        failures = max(0, total - passed) if total else (0 if latest.status == "Пройден" else 1)
        status_label = "OK" if latest.status == "Пройден" else "Проверить"

        self.title = f"Анализ · {latest.title}"
        self.subtitle = summary or latest.subtitle
        self.left = CompareSummary(
            title="До анализа",
            subtitle="нет автоматической оценки смысла",
            profile_match="ручн.",
            stability="ручн.",
            contradiction="ручн.",
        )
        self.right = CompareSummary(
            title="Последний smoke run",
            subtitle=latest.title,
            profile_match=f"{passed}/{total}" if total else "—",
            stability=latest.status,
            contradiction=str(failures),
        )
        self.metrics = (
            CompareMetric("Ответы модели", f"{passed}/{total}" if total else "—", "получено структурных ответов"),
            CompareMetric("Статус запуска", status_label, latest.status),
            CompareMetric("Ошибки", str(failures), "ответ не получен или запуск вернул ошибку"),
        )
        self.insights = self._build_insights(latest.status, passed, total, failures)
        self.deltas = self._build_deltas(latest.status, failures)
        self.samples = cases or (CompareSample("Ответы не найдены", "—", latest.subtitle),)
        return True

    def _parse_experiment_subtitle(self, subtitle: str) -> tuple[str, tuple[CompareSample, ...]]:
        blocks = [block.strip() for block in subtitle.split("\n\n") if block.strip()]
        if not blocks:
            return subtitle, ()
        summary = blocks[0]
        samples: list[CompareSample] = []
        for block in blocks[1:]:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            title = lines[0].replace("CASE ", "Кейс ")
            prompt = next((line.removeprefix("PROMPT: ").strip() for line in lines if line.startswith("PROMPT: ")), "")
            status = next((line.removeprefix("STATUS: ").strip() for line in lines if line.startswith("STATUS: ")), "")
            response = next((line.removeprefix("RESPONSE: ").strip() for line in lines if line.startswith("RESPONSE: ")), "")
            left = f"Промпт: {prompt}" if prompt else "Промпт не сохранён"
            right_parts = []
            if status:
                right_parts.append(f"Статус: {status}")
            if response:
                right_parts.append(f"Ответ: {response}")
            samples.append(CompareSample(title, left, "\n".join(right_parts) if right_parts else block))
        if samples:
            return summary, tuple(samples)
        legacy_lines = [line for line in subtitle.splitlines() if line.strip()]
        legacy_summary = legacy_lines[0] if legacy_lines else subtitle
        legacy_samples = tuple(
            CompareSample(f"Кейс {idx + 1}", "legacy формат", line)
            for idx, line in enumerate(legacy_lines[1:5])
        )
        return legacy_summary, legacy_samples

    def _parse_passed_total(self, summary: str) -> tuple[int, int]:
        # SUMMARY: 3/3 ответов · snapshot
        marker = summary.replace("SUMMARY:", "").strip().split(" ")[0]
        if "/" not in marker:
            return 0, 0
        left, right = marker.split("/", 1)
        try:
            return int(left), int(right)
        except ValueError:
            return 0, 0

    def _build_insights(self, status: str, passed: int, total: int, failures: int) -> tuple[str, ...]:
        if status == "Пройден" and total:
            return (
                f"Smoke-проверка прошла: модель дала {passed} из {total} ответов.",
                "Базовая линия inference работает: модель загружается, генерирует и результат сохраняется.",
                "Качество смысла здесь не оценивается автоматически — ответы нужно просмотреть вручную.",
            )
        return (
            f"Smoke-проверка требует внимания: ошибок {failures}.",
            "Проверьте модель, зависимости inference и содержимое ответов во вкладке «Тесты».",
            "До исправления ошибок не стоит переходить к психологическим/смысловым тестам.",
        )

    def _build_deltas(self, status: str, failures: int) -> tuple[str, ...]:
        if status == "Пройден":
            return (
                "Стабилизирована минимальная цепочка проверки: test run сохраняется и читается анализом.",
                "Следующий шаг: добавить расширенный test pack с ожидаемыми критериями, но без автоматической оценки смысла.",
                "После расширенного test pack можно подключать ручную разметку качества ответов.",
            )
        return (
            f"Есть структурные проблемы тестового запуска: ошибок {failures}.",
            "Нужно добиться чистого smoke run перед расширением тестов.",
            "Анализ сейчас намеренно не делает выводов о личности по неполному запуску.",
        )

    def _apply_analysis_connector(self) -> None:
        if self.analysis_service is None:
            return

        try:
            results = self.analysis_service.list_analysis_results()
        except Exception:
            self.title = "Анализ"
            self.subtitle = "Не удалось загрузить результаты анализа"
            self.insights = ("Не удалось загрузить результаты анализа",)
            self.deltas = ("Не удалось загрузить результаты анализа",)
            self.samples = (
                CompareSample(
                    "Ошибка загрузки",
                    "Не удалось загрузить результаты анализа",
                    "Проверьте подключение к базе данных",
                ),
            )
            self.metrics = (
                CompareMetric("Ответы модели", "—", "Не удалось загрузить результаты анализа"),
                CompareMetric("Статус запуска", "—", "Не удалось загрузить результаты анализа"),
                CompareMetric("Ошибки", "—", "Не удалось загрузить результаты анализа"),
            )
            return

        if not results:
            self.title = "Анализ"
            self.subtitle = "Результаты анализа пока не созданы"
            return

        result = results[0]
        self.title = f"Анализ · {result.result_id}"
        self.subtitle = result.subtitle
        self.left = CompareSummary(
            title=result.left_title,
            subtitle=result.left_subtitle,
            profile_match=result.left_profile_match,
            stability=result.left_stability,
            contradiction=result.left_contradiction,
        )
        self.right = CompareSummary(
            title=result.right_title,
            subtitle=result.right_subtitle,
            profile_match=result.right_profile_match,
            stability=result.right_stability,
            contradiction=result.right_contradiction,
        )
        self.metrics = (
            CompareMetric("Совпадение профиля", result.delta_profile_match, "из реестра анализа"),
            CompareMetric("Стабильность", result.delta_stability, "из реестра анализа"),
            CompareMetric("Противоречия", result.delta_contradiction, "из реестра анализа"),
        )
        self.insights = (result.insight_1, result.insight_2, result.insight_3)
        self.deltas = (result.delta_1, result.delta_2, result.delta_3)
        self.samples = (
            CompareSample(result.sample_1_title, result.sample_1_left, result.sample_1_right),
            CompareSample(result.sample_2_title, result.sample_2_left, result.sample_2_right),
        )
