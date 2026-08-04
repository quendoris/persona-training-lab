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
        "Нажмите следующий этап пайплайна — нужная вкладка откроется автоматически.",
        (
            "Нет ли красных проблем в нижней панели",
            "Свежий ли последний портрет",
            "Есть ли следующий очевидный шаг",
        ),
        "Dashboard показывает сводку; источником истины остаются реальные записи вкладок.",
    ),
    "datasets": InspectorContext(
        "Датасеты",
        "Источник обучающих пар prompt/response.",
        "Добавьте dataset и проверьте структуру. Смысл данных оценивает автор.",
        (
            "Есть поля prompt/response",
            "Нет битого JSON/JSONL",
            "Выбран нужный dataset для обучения",
        ),
        "Не усложняйте валидацию смысла: строгая проверка только структуры.",
    ),
    "training": InspectorContext(
        "Обучение",
        "Запуск fine-tune и сохранение artifact.",
        "Выберите профиль, dataset, модель и запускайте обучение только после зелёной проверки.",
        (
            "Модель найдена",
            "Dataset готов",
            "Логи открываются",
            "После завершения есть artifact path",
        ),
        "Если UI зависает, тяжёлая операция снова попала в главный поток.",
    ),
    "snapshots": InspectorContext(
        "Снимки",
        "Версии модели после обучения.",
        "Проверьте, что последний artifact зарегистрирован как версия модели.",
        (
            "Есть последняя версия",
            "Путь ведёт в artifacts/full_finetune",
            "Версия соответствует последнему run",
        ),
        "Не сравнивайте портреты без понимания, какая версия модели тестировалась.",
    ),
    "tests": InspectorContext(
        "Тесты",
        "Big Five scored portrait выбранной версии модели.",
        "Нажмите «Собрать портрет» и проверьте VALID_SCORE по каждому пункту.",
        (
            "Выбрана точная версия весов",
            "Ответы строго SCORE: 1-5",
            "Ошибки = 0",
            "После теста открыть Анализ",
        ),
        "Если VALID_SCORE=0, KPI строить нельзя: сначала чинить формат ответа.",
    ),
    "analysis": InspectorContext(
        "Анализ",
        "KPI и delta между конкретными версиями модели.",
        "Смотрите Big Five KPI; для delta нужны два сопоставимых портрета.",
        (
            "Есть текущий KPI",
            "Ошибки = 0",
            "Выбраны правильные версии",
            "Батарея и scoring совпадают",
        ),
        "Не подменяйте отсутствующий портрет результатом другой версии.",
    ),
    "profiles": InspectorContext(
        "Профили",
        "Конфигурации личности и режима обучения.",
        "Используйте профиль как источник целевого поведения, но не как результат измерения.",
        (
            "Профиль выбран",
            "Название понятно",
            "Нет конфликта с dataset",
        ),
        "Профиль задаёт цель, а портретные тесты показывают факт после обучения.",
    ),
    "agents": InspectorContext(
        "Агенты",
        "Реальное lineage-дерево моделей, весов, запусков и тестов.",
        "Выберите узел, проверьте зависимости и запускайте действие из карточки версии.",
        (
            "Узел связан с реальными ресурсами",
            "Активные операции блокируют удаление",
            "Сравнение получает точные версии",
            "Локальные ветки не подменяют model registry",
        ),
        "Не удаляйте физические artifacts до появления quarantine и транзакционного GC.",
    ),
    "style": InspectorContext(
        "Внешний вид",
        "Тема, акцент и масштаб интерфейса.",
        "Настройте масштаб так, чтобы рабочие вкладки помещались на ноутбуке.",
        (
            "Масштаб меняется без перезапуска",
            "Sidebar не мешает",
            "Текст читается",
        ),
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
        (
            "Quickstart понятен",
            "Методика описана",
            "Ограничения честно зафиксированы",
        ),
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
        self._runtime_title = QLabel("Операционный контекст")
        self._runtime_title.setObjectName("CardTitle")
        self._runtime = make_muted_label("Активных операций нет.")
        self._issues = make_muted_label("Проблем: 0")

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
        self._layout.addWidget(self._runtime_title)
        self._layout.addWidget(self._runtime)
        self._layout.addWidget(self._issues)
        self._layout.addStretch(1)
        self.set_context("dashboard")

    def set_context(self, screen: str) -> None:
        context = INSPECTOR_CONTEXTS.get(
            screen,
            InspectorContext(
                "Инспектор",
                "Нет отдельной подсказки для этой вкладки.",
                "Работайте по основному сценарию слева направо.",
                (
                    "Понять текущую цель",
                    "Проверить статус",
                    "Перейти к следующей вкладке",
                ),
                "Если непонятно, откройте Документацию → Быстрый старт.",
            ),
        )
        self._title.setText(context.title)
        self._status.setText(context.status)
        self._next.setText(f"Следующий шаг: {context.next_action}")
        for idx, label in enumerate(self._checks):
            label.setText(
                f"• {context.checks[idx]}"
                if idx < len(context.checks)
                else ""
            )
        self._risk.setText(context.risk)

    def set_runtime_context(
        self,
        active_operations: tuple[str, ...],
        issue_count: int,
    ) -> None:
        if active_operations:
            visible = "\n".join(f"• {item}" for item in active_operations[:4])
            remainder = len(active_operations) - 4
            if remainder > 0:
                visible += f"\n• ещё {remainder}"
            self._runtime.setText(visible)
        else:
            self._runtime.setText("Активных операций нет.")
        self._issues.setText(
            "Проблем: 0"
            if issue_count == 0
            else f"Проблем требуют внимания: {issue_count}"
        )
