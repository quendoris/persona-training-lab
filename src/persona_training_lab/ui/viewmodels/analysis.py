from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.analysis.service import AnalysisService


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
    title: str = "Анализ"
    subtitle: str = "Результаты анализа пока не созданы"
    left: CompareSummary = CompareSummary(
        title="нет данных",
        subtitle="ожидание результатов",
        profile_match="—",
        stability="—",
        contradiction="—",
    )
    right: CompareSummary = CompareSummary(
        title="нет данных",
        subtitle="ожидание результатов",
        profile_match="—",
        stability="—",
        contradiction="—",
    )
    metrics: tuple[CompareMetric, ...] = (
        CompareMetric("Совпадение профиля", "—", "Результаты анализа пока не созданы"),
        CompareMetric("Стабильность", "—", "Результаты анализа пока не созданы"),
        CompareMetric("Противоречия", "—", "Результаты анализа пока не созданы"),
    )
    insights: tuple[str, ...] = (
        "Результаты анализа пока не созданы",
    )
    deltas: tuple[str, ...] = (
        "Результаты анализа пока не созданы",
    )
    samples: tuple[CompareSample, ...] = (
        CompareSample(
            "Ожидание результатов",
            "Результаты анализа пока не созданы",
            "Результаты анализа пока не созданы",
        ),
    )

    def __post_init__(self) -> None:
        self._apply_analysis_connector()

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
                CompareMetric("Совпадение профиля", "—", "Не удалось загрузить результаты анализа"),
                CompareMetric("Стабильность", "—", "Не удалось загрузить результаты анализа"),
                CompareMetric("Противоречия", "—", "Не удалось загрузить результаты анализа"),
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
