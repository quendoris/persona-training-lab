from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class DocTopic:
    title: str
    path: str
    summary: str
    next_step: str


DOC_TOPICS: tuple[DocTopic, ...] = (
    DocTopic("Быстрый старт", "docs/quickstart.md", "Минимальный маршрут от датасета до анализа.", "Начните с Датасеты → Обучение → Тесты → Анализ."),
    DocTopic("Пайплайн обучения", "docs/training_pipeline.md", "Как training run превращается в artifact модели.", "После обучения проверьте artifact и локальный ответ модели."),
    DocTopic("Портрет личности", "docs/personality_portrait.md", "Big Five KPI, SCORE-ответы, reverse scoring и дельта.", "Соберите новый портрет после каждого значимого fine-tune."),
    DocTopic("Протокол эксперимента", "docs/experiment_protocol.md", "Что фиксировать, чтобы сравнение было воспроизводимым.", "Перед статьёй сохраняйте версии модели, датасета, батареи и scoring."),
    DocTopic("Ограничения методики", "docs/methodology_limits.md", "Границы интерпретации и честные ограничения текущей батареи.", "Для публикации расширьте батарею и добавьте повторные прогоны."),
)


@dataclass(slots=True)
class DocsService:
    root: Path = Path.cwd()

    def list_topics(self) -> tuple[DocTopic, ...]:
        return DOC_TOPICS

    def read_topic(self, path: str) -> str:
        doc_path = self.root / path
        if not doc_path.exists():
            return f"Документ не найден: {path}"
        return doc_path.read_text(encoding="utf-8")

    def get_quick_start_items(self) -> list[str]:
        return [
            "Датасеты: добавить файл и проверить структуру prompt/response.",
            "Обучение: выбрать модель, датасет, профиль и запустить fine-tune.",
            "Снимки: убедиться, что artifact зарегистрирован.",
            "Тесты: собрать Big Five portrait и проверить VALID_SCORE.",
            "Анализ: сравнить KPI и delta между двумя портретами.",
        ]
