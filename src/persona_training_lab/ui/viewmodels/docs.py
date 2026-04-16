from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.docs.service import DocsService


@dataclass(slots=True)
class DocsViewModel:
    docs_service: DocsService

    def quick_reference(self) -> list[str]:
        return self.docs_service.get_quick_start_items()

    def topics(self) -> list[str]:
        return [
            "С чего начать",
            "Как устроено обучение",
            "Как читать validation",
            "Как фиксировать snapshot",
            "Тестовые наборы и метрики",
            "Быстрая шпаргалка",
        ]

    def context_help(self) -> list[str]:
        return [
            "Подсказка должна оставаться рядом с действием, а не где-то во внешней справке.",
            "Если шаг заблокирован, система должна объяснить причину и следующий ход.",
            "После обучения сначала freeze snapshot, а уже потом независимые тесты.",
        ]
