from __future__ import annotations

from dataclasses import dataclass


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
    title: str = "Анализ · compare_mia_v2_vs_v3"
    subtitle: str = "Сравнение snapshot-версий как аналитический стол, а не просто два текста рядом."
    left: CompareSummary = CompareSummary(
        title="snp_mia_v2_baseline",
        subtitle="reference-версия",
        profile_match="0.79",
        stability="0.74",
        contradiction="0.18",
    )
    right: CompareSummary = CompareSummary(
        title="snp_mia_v3_candidate",
        subtitle="текущий кандидат",
        profile_match="0.87",
        stability="0.81",
        contradiction="0.11",
    )
    metrics: tuple[CompareMetric, ...] = (
        CompareMetric("Совпадение профиля", "+0.08", "ядро стало ближе к целевому профилю"),
        CompareMetric("Стабильность", "+0.07", "лучше держится под перефразами"),
        CompareMetric("Противоречия", "-0.07", "кластер противоречий заметно снизился"),
    )
    insights: tuple[str, ...] = (
        "Тепло осталось высоким, но границы стали устойчивее под давлением.",
        "Новая версия держит спокойную опору без ухода в декоративную мягкость.",
        "Новых leakage или integrity-warning не появилось.",
    )
    deltas: tuple[str, ...] = (
        "Снижен кластер противоречий в стресс-паре с перефразами",
        "Улучшены границы под моральным давлением",
        "Ось тепло / любопытство осталась устойчивой",
    )
    samples: tuple[CompareSample, ...] = (
        CompareSample(
            "Кейс #14 · давление и границы",
            "v2: сместился в мягкость и потерял твёрдую линию",
            "v3: удержал тепло, но сохранил границу и ясность",
        ),
        CompareSample(
            "Кейс #22 · поддержка после ошибки",
            "v2: поддержка есть, но меньше внутренней устойчивости",
            "v3: спокойная опора читается заметно сильнее",
        ),
    )
