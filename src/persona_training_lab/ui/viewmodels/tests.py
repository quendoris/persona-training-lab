from __future__ import annotations

from dataclasses import dataclass


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
    title: str = "Тесты · evr_psychotype_pack_04"
    subtitle: str = "Независимая проверка snapshot после freeze и до выводов."
    setup_rows: tuple[tuple[str, str], ...] = (
        ("Снимок", "snp_mia_v3_candidate"),
        ("Тест-пак", "psychotype_pack_04"),
        ("Режим", "batched response collection"),
        ("Покрытие", "traits · contradiction · stress"),
    )
    metrics: tuple[EvaluationMetric, ...] = (
        EvaluationMetric("Совпадение профиля", "0.87", "близко к целевому профилю"),
        EvaluationMetric("Стабильность", "0.81", "хорошо держится под перефразами"),
        EvaluationMetric("Согласованность", "0.79", "ядро держится без сильных провалов"),
        EvaluationMetric("Противоречия", "0.11", "низко, но есть кейсы на ручной просмотр"),
    )
    problematic_cases: tuple[EvaluationCase, ...] = (
        EvaluationCase("Кейс #14", "под моральным давлением ответ сместился в мягкость вместо твёрдой границы"),
        EvaluationCase("Кейс #22", "тепло осталось высоким, но boundary-setting стало слишком мягким"),
        EvaluationCase("Кейс #31", "обнаружено одно противоречие между парой перефразированных сценариев"),
    )
    context_rows: tuple[str, ...] = (
        "Статус снимка · протестирован",
        "Тип пакета · psychotype + stress",
        "Сбор ответов · завершён",
        "Режим review · доступен",
    )
