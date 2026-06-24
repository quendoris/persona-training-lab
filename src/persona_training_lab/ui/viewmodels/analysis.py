from __future__ import annotations

from dataclasses import dataclass
import re

from persona_training_lab.application.analysis.service import AnalysisService
from persona_training_lab.application.experiments.service import ExperimentsService


SCORE_RE = re.compile(r"\bSCORE\s*:\s*([1-5])\b", re.IGNORECASE)
CASE_HEADER_RE = re.compile(r"(?m)^CASE\s+\d+")
TRAIT_ORDER = ["Extraversion", "Agreeableness", "Conscientiousness", "Emotional Stability", "Openness"]
TRAIT_LABELS = {
    "Extraversion": "E",
    "Agreeableness": "A",
    "Conscientiousness": "C",
    "Emotional Stability": "S",
    "Openness": "O",
}


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


@dataclass(slots=True, frozen=True)
class PortraitStats:
    title: str
    status: str
    summary: str
    passed: int
    total: int
    failures: int
    scores: dict[str, float]
    samples: tuple[CompareSample, ...]


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
        CompareMetric("Дельта", "—", "нужны два портрета"),
        CompareMetric("Ошибки", "—", "тесты пока не запускались"),
    )
    insights: tuple[str, ...] = ("Соберите портрет во вкладке «Тесты».",)
    deltas: tuple[str, ...] = ("После двух SCORE-прогонов анализ рассчитает изменение факторов.",)
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
        previous = experiments[1] if len(experiments) > 1 else None
        self._apply_experiment(experiments[0], previous)

    def _apply_experiment(self, latest: object, previous: object | None = None) -> None:
        latest_stats = self._stats_from_experiment(latest)
        previous_stats = self._stats_from_experiment(previous) if previous is not None else None
        profile_type = self._profile_type(latest_stats.scores)
        score_line = self._score_line(latest_stats.scores)
        delta_line = self._delta_line(previous_stats.scores, latest_stats.scores) if previous_stats else "нужны 2 портрета"

        self.title = f"Анализ · {latest_stats.title}"
        self.subtitle = latest_stats.summary
        if previous_stats is not None:
            self.left = CompareSummary(
                "Предыдущий портрет",
                previous_stats.title,
                self._score_line(previous_stats.scores) or "—",
                previous_stats.status,
                str(previous_stats.failures),
            )
        else:
            self.left = CompareSummary("Метод", "Big Five / IPIP-style KPI", "1-5", "reverse", "manual")
        self.right = CompareSummary(
            "Последний портрет",
            latest_stats.title,
            f"{latest_stats.passed}/{latest_stats.total}" if latest_stats.total else "—",
            latest_stats.status,
            str(latest_stats.failures),
        )
        self.metrics = (
            CompareMetric("Big Five KPI", score_line or "—", "текущий средний балл по валидным SCORE"),
            CompareMetric("Дельта", delta_line, "latest - previous по факторам"),
            CompareMetric("Ошибки", str(latest_stats.failures), "пункты без валидного SCORE"),
        )
        self.insights = self._build_insights(latest_stats, previous_stats, profile_type)
        self.deltas = self._build_delta_notes(latest_stats, previous_stats)
        self.samples = self._compare_samples(latest_stats, previous_stats)

    def _stats_from_experiment(self, experiment: object | None) -> PortraitStats:
        if experiment is None:
            return PortraitStats("—", "—", "—", 0, 0, 0, {}, ())
        subtitle = getattr(experiment, "subtitle", "")
        status = getattr(experiment, "status", "")
        title = getattr(experiment, "title", "")
        summary, samples, trait_values, invalid_count = self._parse_big_five(subtitle)
        passed, total = self._parse_passed_total(summary)
        failures = max(invalid_count, max(0, total - passed)) if total else invalid_count
        if not total and status not in {"Портрет собран", "Пройден"}:
            failures = max(failures, 1)
        return PortraitStats(
            title=title,
            status=status,
            summary=summary or subtitle,
            passed=passed,
            total=total,
            failures=failures,
            scores=self._trait_scores(trait_values),
            samples=samples,
        )

    def _split_case_records(self, subtitle: str) -> tuple[str, list[str]]:
        match = CASE_HEADER_RE.search(subtitle)
        if match is None:
            return subtitle.strip(), []
        summary = subtitle[: match.start()].strip()
        records = [record.strip() for record in CASE_HEADER_RE.split(subtitle[match.start():]) if record.strip()]
        headers = CASE_HEADER_RE.findall(subtitle[match.start():])
        return summary, [f"{header}\n{record}" for header, record in zip(headers, records, strict=False)]

    def _parse_big_five(self, subtitle: str) -> tuple[str, tuple[CompareSample, ...], dict[str, list[float]], int]:
        summary, blocks = self._split_case_records(subtitle)
        if not summary and not blocks:
            return subtitle, (), {}, 0
        samples: list[CompareSample] = []
        trait_values: dict[str, list[float]] = {}
        invalid_count = 0
        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            title = lines[0].replace("CASE ", "Пункт ")
            trait = self._field(lines, "TRAIT") or self._field(lines, "DIMENSION")
            key = self._field(lines, "KEY")
            reverse = self._field(lines, "REVERSE") == "1"
            valid_score = self._field(lines, "VALID_SCORE")
            item = self._field(lines, "ITEM") or self._field(lines, "QUESTION") or self._field(lines, "PROMPT")
            status = self._field(lines, "STATUS")
            response = self._field(lines, "RESPONSE")
            raw_response = self._field(lines, "RAW_RESPONSE")
            raw_score = self._score_from_response(response)
            score = 6 - raw_score if raw_score is not None and reverse else raw_score
            if raw_score is None or valid_score == "0":
                invalid_count += 1
            elif trait and score is not None:
                trait_values.setdefault(trait, []).append(float(score))
            left = "\n".join(part for part in (f"Фактор: {trait}" if trait else "", f"Ключ: {key}" if key else "", f"Пункт: {item}" if item else "") if part)
            right = "\n".join(
                part
                for part in (
                    f"Статус: {status}" if status else "",
                    f"Raw: {raw_score}" if raw_score is not None else "Raw: —",
                    f"Score: {score}" if score is not None else "Score: —",
                    f"Ответ: {response}" if response else "",
                    f"Raw response: {raw_response}" if raw_response and raw_response != response else "",
                )
                if part
            )
            samples.append(CompareSample(title, left or "Пункт не сохранён", right or block))
        return summary, tuple(samples), trait_values, invalid_count

    def _field(self, lines: list[str], name: str) -> str:
        prefix = f"{name}: "
        return next((line.removeprefix(prefix).strip() for line in lines if line.startswith(prefix)), "")

    def _score_from_response(self, response: str) -> int | None:
        match = SCORE_RE.search(response)
        return int(match.group(1)) if match else None

    def _trait_scores(self, values: dict[str, list[float]]) -> dict[str, float]:
        return {trait: round(sum(items) / len(items), 2) for trait, items in values.items() if items}

    def _score_line(self, scores: dict[str, float]) -> str:
        return " · ".join(f"{TRAIT_LABELS[key]}={scores[key]:.2f}" for key in TRAIT_ORDER if key in scores)

    def _delta_line(self, previous: dict[str, float], latest: dict[str, float]) -> str:
        parts: list[str] = []
        for key in TRAIT_ORDER:
            if key not in previous or key not in latest:
                continue
            delta = latest[key] - previous[key]
            parts.append(f"{TRAIT_LABELS[key]}={delta:+.2f}")
        return " · ".join(parts) if parts else "нет общей базы"

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

    def _build_insights(self, latest: PortraitStats, previous: PortraitStats | None, profile_type: str) -> tuple[str, ...]:
        if not latest.scores:
            return (
                "SCORE-значения не распознаны: проверьте ответы модели во вкладке «Тесты».",
                "Модель должна возвращать строго SCORE: 1-5.",
                "Без чисел анализ не строит KPI и тип профиля.",
            )
        strongest = max(latest.scores.items(), key=lambda item: item[1])
        if previous is None or not previous.scores:
            return (
                f"Портрет собран: {latest.passed}/{latest.total} пунктов, статус: {latest.status}.",
                f"Тип текущего профиля: {profile_type}.",
                "Для расчёта дельты нужен ещё один портрет после следующего fine-tune или нового запуска.",
            )
        biggest_trait, biggest_delta = self._largest_abs_delta(previous.scores, latest.scores)
        return (
            f"Портрет собран: {latest.passed}/{latest.total} пунктов, статус: {latest.status}.",
            f"Сильнейший текущий фактор: {strongest[0]} = {strongest[1]:.2f}.",
            f"Самое заметное изменение: {biggest_trait} {biggest_delta:+.2f}.",
        )

    def _build_delta_notes(self, latest: PortraitStats, previous: PortraitStats | None) -> tuple[str, ...]:
        if previous is None or not previous.scores or not latest.scores:
            return (
                "Для научного сравнения нужны минимум два портретных прогона.",
                "После следующего fine-tune запустите «Собрать портрет» ещё раз.",
                "Анализ автоматически покажет latest - previous по каждому фактору.",
            )
        notes = [f"{trait}: {previous.scores[trait]:.2f} → {latest.scores[trait]:.2f} ({latest.scores[trait] - previous.scores[trait]:+.2f})" for trait in TRAIT_ORDER if trait in previous.scores and trait in latest.scores]
        return tuple(notes) or ("Нет общей базы факторов для сравнения.",)

    def _compare_samples(self, latest: PortraitStats, previous: PortraitStats | None) -> tuple[CompareSample, ...]:
        if previous is None or not previous.samples:
            return latest.samples or (CompareSample("Ответы не найдены", "—", latest.summary),)
        compared: list[CompareSample] = []
        for idx, sample in enumerate(latest.samples[:10]):
            left = previous.samples[idx].right_note if idx < len(previous.samples) else "предыдущий пункт отсутствует"
            compared.append(CompareSample(sample.title, left, sample.right_note))
        return tuple(compared)

    def _largest_abs_delta(self, previous: dict[str, float], latest: dict[str, float]) -> tuple[str, float]:
        common = [(trait, latest[trait] - previous[trait]) for trait in TRAIT_ORDER if trait in previous and trait in latest]
        if not common:
            return "нет общей базы", 0.0
        return max(common, key=lambda item: abs(item[1]))

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
