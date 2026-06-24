from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.docs.service import DocTopic, DocsService


@dataclass(slots=True)
class DocsViewModel:
    docs_service: DocsService

    def quick_reference(self) -> list[str]:
        return self.docs_service.get_quick_start_items()

    def topics(self) -> tuple[DocTopic, ...]:
        return self.docs_service.list_topics()

    def topic_content(self, path: str) -> str:
        return self.docs_service.read_topic(path)

    def context_help(self) -> list[str]:
        return [
            "Документация должна отвечать на вопрос: что делать следующим шагом.",
            "Если вкладка непонятна — откройте соответствующий раздел и проверьте чеклист.",
            "Для исследования всегда фиксируйте версии: модель, датасет, батарея, scoring.",
        ]
