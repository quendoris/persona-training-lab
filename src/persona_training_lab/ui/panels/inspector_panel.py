from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from persona_training_lab.ui.components.panels import make_muted_label


@dataclass(slots=True, frozen=True)
class InspectorContext:
    title: str
    status: str
    next_action: str
    checks: tuple[str, ...]
    risk: str


INSPECTOR_CONTEXTS: dict[str, InspectorContext] = {
    "dashboard": InspectorContext(
        "Главный экран",
        "Обзор состояния проекта.",
        "Проверьте, есть ли свежий training run, snapshot и portrait delta.",
        ("Нет ли красных проблем в нижней панели", "Свежий ли последний портрет", "Есть ли следующий очевидный шаг"),
        "Не принимайте dashboard за источник истины: для деталей переходите во вкладку.",
    ),
    "datasets": InspectorContext(
        "Датасеты",
        "Источник обучающих пар prompt/response.",
        "Добавьте dataset и проверьте структуру. Смысл данных оценивает автор.",
        ("Есть поля prompt/response", "Нет битого JSON/JSONL", "Выбран нужный dataset для обучения"),
        "Не усложняйте валидацию смысла: строгая проверка только структуры.",
    ),
    "training": InspectorContext(
        "Обучение",
        "Запуск fine-tune и сохранение artifact.",
        "Выберите профиль, dataset, модель и запускайте обучение только после зелёной проверки.",
        ("Модель найдена", "Dataset готов", "Логи открываются", "После завершения есть artifact path"),
        "Если UI зависает, тяжёлая операция снова попала в главный поток.",
    ),
    "snapshots": InspectorContext(
        "Снимки",
        "Версии модели после обучения.",
        "Проверьте, что последний artifact зарегистрирован как версия модели.",
        ("Есть последняя версия", "Путь ведёт в artifacts/full_finetune", "Версия соответствует последнему run"),
        "Не сравнивайте портреты без понимания, какая версия модели тестировалась.",
    ),
    "tests": InspectorContext(
        "Тесты",
        "Big Five scored portrait текущей модели.",
        "Нажмите «Собрать портрет» и проверьте VALID_SCORE по каждому пункту.",
        ("Ответы строго SCORE: 1-5", "Ошибки = 0", "Пункты не разваливаются на карточки", "После теста открыть Анализ"),
        "Если VALID_SCORE=0, KPI строить нельзя: сначала чинить формат ответа.",
    ),
    "analysis": InspectorContext(
        "Анализ",
        "KPI и delta между портретами модели.",
        "Смотрите Big Five KPI; для delta нужны минимум два портретных запуска.",
        ("Есть текущий KPI", "Ошибки = 0", "При двух портретах появилась delta", "Сравнение latest - previous"),
        "Не делайте выводы по старому портрету: после fine-tune запускайте тест заново.",
    ),
    "profiles": InspectorContext(
        "Профили",
        "Конфигурации личности/режима обучения.",
        "Используйте профиль как источник целевого поведения, но не как результат измерения.",
        ("Профиль выбран", "Название понятно", "Нет конфликта с dataset"),
        "Профиль задаёт цель, а портретные тесты показывают факт после обучения.",
    ),
    "agents": InspectorContext(
        "Агенты",
        "Будущие помощники исследования и разметки.",
        "Пока используйте как план: исследователь, разметчик, аудитор dataset.",
        ("Определить роли", "Не смешивать агента и модель", "Не доверять автооценке без ручной проверки"),
        "Агенты не должны принимать решения за автора эксперимента.",
    ),
    "style": InspectorContext(
        "Внешний вид",
        "Тема, акцент и масштаб интерфейса.",
        "Настройте масштаб так, чтобы рабочие вкладки помещались на ноутбуке.",
        ("Масштаб меняется без перезапуска", "Sidebar не мешает", "Текст читается"),
        "Оптимизация внешнего вида вторична: сначала рабочие пайплайны.",
    ),
    "keybindings": InspectorContext(
        "Назначения клавиш",
        "Живые сочетания команд графа и справочник жестов canvas.",
        "Измените одну комбинацию, вернитесь в «Агенты» и проверьте её без перезапуска.",
        (
            "Нет конфликтов между командами",
            "Новое сочетание применяется сразу",
            "После перезапуска значение сохраняется",
            "Сброс возвращает стандартный физический guard",
        ),
        "Не назначайте системные сочетания рабочего окружения, если compositor забирает их раньше Qt.",
    ),
    "docs": InspectorContext(
        "Документация",
        "Живые markdown-разделы проекта.",
        "Откройте нужный раздел и следуйте короткому чеклисту справа.",
        ("Quickstart понятен", "Методика описана", "Ограничения честно зафиксированы"),
        "Документация должна помогать действию, а не превращаться в красивую стену текста.",
    ),
}


class InspectorPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(10)

        self._title = QLabel("Инспектор")
        self._title.setObjectName("SectionTitle")
        self._status = make_muted_label("Контекстная подсказка по текущей вкладке.")
        self._next = QLabel("Выберите вкладку слева.")
        self._next.setWordWrap(True)
        self._next.setObjectName("CardTitle")
        self._checks_title = QLabel("Проверить")
        self._checks_title.setObjectName("CardTitle")
        self._checks: list[QLabel] = []
        self._risk = make_muted_label("Риск появится здесь.")

        self._layout.addWidget(self._title)
        self._layout.addWidget(self._status)
        self._layout.addWidget(self._next)
        self._layout.addWidget(self._checks_title)
        for _ in range(4):
            label = make_muted_label("—")
            self._checks.append(label)
            self._layout.addWidget(label)
        self._layout.addWidget(QLabel("Риск"))
        self._layout.addWidget(self._risk)
        self._layout.addStretch(1)
        self.set_context("dashboard")

    def set_context(self, screen: str) -> None:
        context = INSPECTOR_CONTEXTS.get(
            screen,
            InspectorContext(
                "Инспектор",
                "Нет отдельной подсказки для этой вкладки.",
                "Работайте по основному сценарию слева направо.",
                ("Понять текущую цель", "Проверить статус", "Перейти к следующей вкладке"),
                "Если непонятно, откройте Документацию → Быстрый старт.",
            ),
        )
        self._title.setText(context.title)
        self._status.setText(context.status)
        self._next.setText(f"Следующий шаг: {context.next_action}")
        for idx, label in enumerate(self._checks):
            label.setText(f"• {context.checks[idx]}" if idx < len(context.checks) else "")
        self._risk.setText(context.risk)
