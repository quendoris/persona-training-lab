from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DocsService:
    def get_quick_start_items(self) -> list[str]:
        return [
            "Сначала выбери базовую модель.",
            "Потом выбери профиль личности.",
            "Проверь и утверди версию датасета.",
            "Запусти обучение и зафиксируй snapshot.",
            "Тестируй snapshot отдельно от training run.",
        ]
