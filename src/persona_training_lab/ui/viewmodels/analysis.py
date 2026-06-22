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
        subtitle="ожидание портретных тестов",
        profile_match="—",
        stability="—",
        contradiction="—",
    )
    right: CompareSummary = CompareSummary(
        title="последний портрет",
        subtitle="ожидание результатов тестов",
        profile_match="—",
        stability="—",
        contradiction="—",
    )
    metrics: tuple[CompareMetric, ...] = (
        CompareMetric("Измерения портрета", "—", "Тесты пока не запускались"),
        CompareMetric("Статус запуска", "—", "Тесты пока не запускались"),
        CompareMetric("Ошибки", "—", "Тесты пока не запускались"),
    )
    insights: tuple[str, ...] = ("Результаты анализа пока не созданы",)
    deltas: tuple[str, ...] = ("Соберите психологический портрет во вкладке «Тесты», затем откройте анализ.",)
    samples: tuple[CompareSample, ...] = (
        CompareSample("Ожидание результатов", "Тесты пока не запускались", "Ответы модели пока не сохранены"),
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
            self.left = CompareSummary("Ожидание", "нет сохранённых портретов", "—", "—", "—")
            self.right = CompareSummary("Психологический портрет", "ещё не собран", "—", "—", "—")
            self.metrics = (
                CompareMetric("Измерения портрета", "0/0", "Нет сохранённых portrait test runs"),
                CompareMetric("Статус запуска", "—", "Соберите портрет во вкладке «Тесты»"),
                CompareMetric("Ошибки", "—", "Нет данных"),
            )
            self.insights = (
                "Анализ ждёт реальные результаты из вкладки «Тесты».",
                "Сейчас выводы не строятся, чтобы не показывать декоративные метрики.",
                "Сначала нужно собрать хотя бы один психологический портрет текущей модели.",
            )
            self.deltas = (
                "Следующий шаг: открыть «Тесты» и нажать «Собрать портрет».",
                "После сохранения результата кнопка «Открыть анализ» переведёт сюда автоматически.",
                "Автологика анализирует полноту и статус; смысл ответов размечается вручную.",
            )
            self.samples = (CompareSample("Нет кейсов", "—", "Нет сохранённых портретных ответов"),)
            return True

        latest = experiments[0]
        summary, cases = self._parse_experiment_subtitle(latest.subtitle)
        passed, total = self._parse_passed_total(summary)
        success_status = latest.status in {"Портрет собран", "Пройден"}
        failures = max(0, total - passed) if total else (0 if success_status else 1)
        status_label = "OK" if success_status else "Проверить"

        self.title = f"Анализ · {latest.title}"
        self.subtitle = summary or latest.subtitle
        self.left = CompareSummary(
            title="Цель анализа",
            subtitle="устойчивая личность после изменения весов",
            profile_match="ручн.",
            stability="ручн.",
            contradiction="ручн.",
        )
        self.right = CompareSummary(
            title="Последний психологический портрет",
            subtitle=latest.title,
            profile_match=f"{passed}/{total}" if total else "—",
            stability=latest.status,
            contradiction=str(failures),
        )
        self.metrics = (
            CompareMetric("Измерения портрета", f"{passed}/{total}" if total else "—", "получено ответов по нейтральным вопросам"),
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
            dimension = next((line.removeprefix("DIMENSION: ").strip() for line in lines if line.startswith("DIMENSION: ")), "")
            question = next((line.removeprefix("QUESTION: ").strip() for line in lines if line.startswith("QUESTION: ")), "")
            prompt = next((line.removeprefix("PROMPT: ").strip() for line in lines if line.startswith("PROMPT: ")), "")
            status = next((line.removeprefix("STATUS: ").strip() for line in lines if line.startswith("STATUS: ")), "")
            response = next((line.removeprefix("RESPONSE: ").strip() for line in lines if line.startswith("RESPONSE: ")), "")
            left_parts = []
            if dimension:
                left_parts.append(f"Измерение: {dimension}")
            if question:
                left_parts.append(f"Вопрос: {question}")
            elif prompt:
                left_parts.append(f"Промпт: {prompt}")
            right_parts = []
            if status:
                right_parts.append(f"Статус: {status}")
            if response:
                right_parts.append(f"Ответ: {response}")
            samples.append(
                CompareSample(
                    title,
                    "\n".join(left_parts) if left_parts else "Вопрос не сохранён",
                    "\n".join(right_parts) if right_parts else block,
                )
            )
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
        marker = summary.replace("PORTRAIT:", "").replace("SUMMARY:", "").strip().split(" ")[0]
        if "/" not in marker:
            return 0, 0
        left, right = marker.split("/", 1)
        try:
            return int(left), int(right)
        except ValueError:
            return 0, 0

    def _build_insights(self, status: str, passed: int, total: int, failures: int) -> tuple[str, ...]:
        if status in {"Портрет собран", "Пройден"} and total:
            return (
                f"Портретный тест прошёл: модель дала {passed} из {total} ответов по нейтральным вопросам.",
                "Теперь можно смотреть фактическую жёсткость, инициативу, границы, честность и реакцию на сбой без подсказанного поведения.",
                "Качество личности не оценивается числом автоматически — нужна ручная разметка стабильности и желательности ответов.",
            )
        return (
            f"Портретный тест требует внимания: ошибок {failures}.",
            "Проверьте модель, зависимости inference и ответы во вкладке «Тесты».",
            "До чистого портретного прогона рано делать выводы об устойчивой личности модели.",
        )

    def _build_deltas(self, status: str, failures: int) -> tuple[str, ...]:
        if status in {"Портрет собран", "Пройден"}:
            return (
                "Цепочка тестирования теперь диагностическая: вопросы не подсказывают нужный характер ответа.",
                "Следующий шаг: добавить ручную разметку по каждому измерению — подходит / слабо / требует дообучения.",
                "После разметки можно строить датасет коррекции именно по слабым чертам личности.",
            )
        return (
            f"Есть структурные проблемы портретного запуска: ошибок {failures}.",
            "Нужно добиться полного portrait run перед расширением психологических тестов.",
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
                CompareMetric("Измерения портрета", "—", "Не удалось загрузить результаты анализа"),
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
