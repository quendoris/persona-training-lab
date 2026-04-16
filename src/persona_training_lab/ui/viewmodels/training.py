from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class TrainingMetric:
    title: str
    value: str
    note: str


@dataclass(slots=True, frozen=True)
class CheckpointView:
    name: str
    note: str
    highlighted: bool = False


@dataclass(slots=True)
class TrainingViewModel:
    title: str = "Обучение · trn_qwen2b_mia_014"
    subtitle: str = "Persona Imprint · Qwen 2B · Mia core v3 · curated_rose v07"
    status: str = "выполняется · checkpoint-safe"
    selected_objects: tuple[tuple[str, str], ...] = (
        ("Базовая модель", "Qwen 2B"),
        ("Профиль", "Mia core v3"),
        ("Версия датасета", "curated_rose v07"),
        ("Режим", "Persona Imprint"),
    )
    stat_cards: tuple[TrainingMetric, ...] = (
        TrainingMetric("Эпоха", "3 / 8", "Шаг 18 420"),
        TrainingMetric("Loss", "1.42", "ровное снижение"),
        TrainingMetric("Скорость", "61 ток/с", "сеанс стабилен"),
        TrainingMetric("Чекпоинты", "05", "следующий через 11 мин"),
    )
    checkpoints: tuple[CheckpointView, ...] = (
        CheckpointView("chk_001", "epoch 1 · validated"),
        CheckpointView("chk_002", "epoch 2 · стабильная кривая"),
        CheckpointView("chk_003", "epoch 2.5 · drift снижается"),
        CheckpointView("chk_004", "epoch 3 · лучший кандидат", True),
    )
    logs: tuple[str, ...] = (
        "[10:21:04] training started",
        "[10:22:11] checkpoint policy applied",
        "[10:23:32] monitor: GPU 63°C · VRAM 14.8/16 GB",
        "[10:24:08] metric hint: contradiction risk stable",
        "[10:25:46] checkpoint chk_004 registered",
    )
    monitor_rows: tuple[tuple[str, int, str], ...] = (
        ("Нагрузка GPU", 78, "63°C"),
        ("Видеопамять", 92, "14.8 / 16 ГБ"),
        ("Память RAM", 52, "50 / 96 ГБ"),
    )
    risk_title: str = "Мягкое предупреждение"
    risk_body: str = "Запас по памяти уже узкий, но стабильный. Лучше не повышать sequence length в этом запуске."
    next_step: str = "После завершения система предложит зафиксировать run как snapshot перед тестированием."
