from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.docs.service import DocsService


@dataclass(slots=True)
class DashboardViewModel:
    docs_service: DocsService

    def quick_actions(self) -> list[tuple[str, str, str]]:
        return [
            ("▶", "Новый запуск обучения", "Собрать новый pipeline imprint для личности."),
            ("✓", "Проверить датасет", "Проверить curated-датасет перед обучением."),
            ("⇄", "Сравнить версии", "Сравнить две версии личности и увидеть дельту."),
        ]

    def quick_start(self) -> list[str]:
        return self.docs_service.get_quick_start_items()

    def stats(self) -> list[tuple[str, str, str]]:
        return [
            ("Активные запуски", "02", "1 обучение · 1 тестирование"),
            ("Снимки", "14", "3 одобрено · 2 архивировано"),
            ("Датасеты", "07", "2 требуют внимания"),
            ("Риски", "03", "критических сбоев нет"),
        ]

    def recent_activity(self) -> list[tuple[str, str]]:
        return [
            ("Запуск обучения trn_qwen2b_014", "checkpoint сохранён · 12 минут назад"),
            ("Снимок snp_mia_persona_v3", "помечен как проверенный"),
            ("Версия датасета dsv_curated_rose_07", "одобрена для обучения"),
            ("Оценочный прогон evr_psychotype_pack_04", "завершён с предупреждениями"),
        ]

    def system_metrics(self) -> list[tuple[str, int, str]]:
        return [
            ("Нагрузка GPU", 76, "16 ГБ VRAM · 63°C"),
            ("Память RAM", 58, "96 ГБ всего · стабильно"),
            ("Целостность артефактов", 92, "2 предупреждения · 0 критических"),
        ]

    def attention_items(self) -> list[tuple[str, str]]:
        return [
            (
                "Следующий лучший шаг",
                "Зафиксируй завершённый запуск в снимок перед стартом тестов.",
            ),
            (
                "Заметка по целостности",
                "Один артефакт телеметрии ждёт проверки перед очисткой.",
            ),
            (
                "Быстрый вход в docs",
                "Гайд по preflight обновлён под curated-датасеты.",
            ),
        ]

    def quick_lineage(self) -> list[str]:
        return [
            "Базовая модель · Qwen 2B",
            "Профиль личности · Mia / устойчивое ядро",
            "Версия датасета · curated_v07",
            "Запуск обучения · trn_014",
            "Снимок · snp_v3_candidate",
        ]
