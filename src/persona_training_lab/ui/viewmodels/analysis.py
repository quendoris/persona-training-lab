from __future__ import annotations

from dataclasses import dataclass
import re

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
    subtitle: str = "Нет результатов тестов для анализа"
    left: CompareSummary = CompareSummary("Метод", "Big Five scored items", "ручн.", "ручн.", "ручн.")
    right: CompareSummary = CompareSummary("Последний портрет", "ожидание", "—", "—", "—")
    metrics: tuple[CompareMetric, ...] = (
        CompareMetric("Big Five KPI", "—", "тесты пока не запускались"),
        CompareMetric("Тип профиля", "—", "тесты пока не запускались"),
        CompareMetric("Ошибки", "—", "тесты пока не запускались"),
    )
    insights: tuple[str, ...] = ("Соберите портрет во вкладке «Тесты».",)
    deltas: tuple[str, ...] = ("После SCORE-ответов анализ рассчитает средние значения по факторам.",)
    samples: tuple[CompareSample, ...] = (CompareSample("Нет данных", "—", "Нет сохранённых ответов"),)

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        if self.experiments_service is None:
            self._apply_analysis_connector()
            return
        try:
            experiments = self.experiments_service.list_experiments()
        except Exception:
            self.title = "Анализ"
            self.subtitle = "Не удалось загрузить результаты тестов"
            self.insights = ("Проверьте SQLite-реестр experiments.",)
            return
        if not experiments:
            self.title = "Анализ"
            self.subtitle = "Нет результатов тестов для анализа"
            return
        self._apply_experiment(experiments[0])

    def _apply_experiment(self, latest: object) -> None:
        subtitle = getattr(latest, "subtitle", "")
        status = getattr(latest, "status", "")
        title = getattr(latest, "title", "")
        summary, samples, trait_values = self._parse_big_five(subtitle)
        passed, total = self._parse_passed_total(summary)
        failures = max(0, total - passed) if total else (0 if status in {"Портрет собран", "Пройден"} else 1)
        trait_scores = self._trait_scores(trait_values)
        profile_type = self._profile_type(trait_scores)
        score_line = self._score_line(trait_scores)

        self.title = f"Анализ · {title}"
        self.subtitle = summary or subtitle
        self.left = CompareSummary("Метод", "Big Five / IPIP-style KPI", "1-5", "reverse", "manual")
        self.right = CompareSummary("Последний портрет", title, f"{passed}/{total}" if total else "—", status, str(failures))
        self.metrics = (
            CompareMetric("Big Five KPI", score_line or "—", "средний балл по факторам 1-5"),
            CompareMetric("Тип профиля", profile_type, "эвристический ярлык по двум самым высоким факторам"),
            CompareMetric("Ошибки", str(failures), "пункты без валидного SCORE"),
        )
        self.insights = self._build_insights(trait_scores, status, passed, total)
        self.deltas = (
            "Теперь тест даёт численные KPI, пригодные для сравнения версий модели.",
            "Следующий слой: сохранить ручную оценку качества по каждому фактору и собрать corrective dataset.",
            "Для статьи нужно фиксировать версию батареи, модель, seed/режим генерации и правила score parsing.",
        )
        self.samples = samples or (CompareSample("Ответы не найдены", "—", subtitle),)

    def _parse_big_five(self, subtitle: str) -> tuple[str, tuple[CompareSample, ...], dict[str, list[float]]]:
        blocks = [block.strip() for block in subtitle.split("\n\n") if block.strip()]
        if not blocks:
            return subtitle, (), {}
        summary = blocks[0]
        samples: list[CompareSample] = []
        trait_values: dict[str, list[float]] = {}
        for block in blocks[1:]:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            title = lines[0].replace("CASE ", "Пункт ")
            trait = self._field(lines, "TRAIT") or self._field(lines, "DIMENSION")
            key = self._field(lines, "KEY")
            reverse = self._field(lines, "REVERSE") == "1"
            item = self._field(lines, "ITEM") or self._field(lines, "QUESTION") or self._field(lines, "PROMPT")
            status = self._field(lines, "STATUS")
            response = self._field(lines, "RESPONSE")
            raw_score = self._score_from_response(response)
            score = 6 - raw_score if raw_score is not None and reverse else raw_score
            if trait and score is not None:
                trait_values.setdefault(trait, []).append(float(score))
            left = "\n".join(part for part in (f"Фактор: {trait}" if trait else "", f"Ключ: {key}" if key else "", f"Пункт: {item}" if item else "") if part)
            right = "\n".join(part for part in (f"Статус: {status}" if status else "", f"Raw: {raw_score}" if raw_score is not None else "Raw: —", f"Score: {score}" if score is not None else "Score: —", f"Ответ: {response}" if response else "") if part)
            samples.append(CompareSample(title, left or "Пункт не сохранён", right or block))
        return summary, tuple(samples), trait_values

    def _field(self, lines: list[str], name: str) -> str:
        prefix = f"{name}: "
        return next((line.removeprefix(prefix).strip() for line in lines if line.startswith(prefix)), "")

    def _score_from_response(self, response: str) -> int | None:
        match = re.search(r"\b([1-5])\b", response)
        return int(match.group(1)) if match else None

    def _trait_scores(self, values: dict[str, list[float]]) -> dict[str, float]:
        return {trait: round(sum(items) / len(items), 2) for trait, items in values.items() if items}

    def _score_line(self, scores: dict[str, float]) -> str:
        order = ["Extraversion", "Agreeableness", "Conscientiousness", "Emotional Stability", "Openness"]
        return " · ".join(f"{key[:1]}={scores[key]:.2f}" for key in order if key in scores)

    def _profile_type(self, scores: dict[str, float]) -> str:
        if not scores:
            return "нет score"
        top = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:2]
        return " + ".join(name for name, _ in top)

    def _parse_passed_total(self, summary: str) -> tuple[int, int]:
        marker = summary.replace("PORTRAIT:", "").replace("SUMMARY:", "").strip().split(" ")[0]
        if "/" not in marker:
            return 0, 0
        left, right = marker.split("/", 1)
        try:
            return int(left), int(right)
        except ValueError:
            return 0, 0

    def _build_insights(self, scores: dict[str, float], status: str, passed: int, total: int) -> tuple[str, ...]:
        if not scores:
            return (
                "SCORE-значения не распознаны: проверьте ответы модели во вкладке «Тесты».",
                "Модель должна возвращать строго SCORE: 1-5.",
                "Без чисел анализ не строит KPI и тип профиля.",
            )
        strongest = max(scores.items(), key=lambda item: item[1])
        weakest = min(scores.items(), key=lambda item: item[1])
        return (
            f"Портрет собран: {passed}/{total} пунктов, статус: {status}.",
            f"Сильнейший фактор сейчас: {strongest[0]} = {strongest[1]:.2f}.",
            f"Самый слабый фактор сейчас: {weakest[0]} = {weakest[1]:.2f}.",
        )

    def _apply_analysis_connector(self) -> None:
        if self.analysis_service is None:
            return
        try:
            results = self.analysis_service.list_analysis_results()
        except Exception:
            return
        if results:
            result = results[0]
            self.title = f"Анализ · {result.result_id}"
            self.subtitle = result.subtitle
