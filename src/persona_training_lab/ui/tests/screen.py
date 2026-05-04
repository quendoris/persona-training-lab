from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.tests import TestsViewModel


def _stable_scroll_shell(min_height: int = 340, *, shell_margins: tuple[int, int, int, int] = (14, 14, 14, 14), spacing: int = 10) -> tuple[QScrollArea, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setObjectName("StableScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setMinimumHeight(min_height)
    apply_scrollbar_style(scroll)

    outer = QFrame()
    outer.setObjectName("StableScrollShell")

    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(*shell_margins)
    outer_layout.setSpacing(0)

    wrap = QWidget()
    wrap.setObjectName("TestsScrollWrap")
    wrap.setStyleSheet(
        """
        QWidget#TestsScrollWrap {
            background: transparent;
            border: none;
        }
        """
    )

    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)

    outer_layout.addWidget(wrap)
    scroll.setWidget(outer)
    return scroll, layout


class TestsScreen(QWidget):
    def __init__(self, view_model: TestsViewModel) -> None:
        super().__init__()
        self._vm = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("ShellHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(22, 20, 22, 20)
        hl.setSpacing(8)

        title = QLabel(self._vm.title)
        title.setObjectName("ScreenTitle")
        subtitle = make_muted_label(self._vm.subtitle)

        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(header)

        actions = QFrame()
        actions.setObjectName("PanelCardSoft")
        al = QHBoxLayout(actions)
        al.setContentsMargins(18, 14, 18, 14)
        al.setSpacing(10)

        for index, text in enumerate(["Запустить проверку", "Открыть анализ", "Разобрать кейсы"]):
            btn = QPushButton(text)
            if index:
                btn.setObjectName("SecondaryButton")
            al.addWidget(btn)

        al.addStretch(1)
        root.addWidget(actions)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        # Левый блок: контекст проверки
        left = PanelCard("Контекст проверки", "Мы тестируем snapshot, а не training run напрямую.")
        setup_scroll, setup_layout = _stable_scroll_shell(340)

        for key, value in self._vm.setup_rows:
            row = QFrame()
            row.setObjectName("PanelCardSoft")

            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(10)

            rl.addWidget(make_muted_label(key))
            rl.addStretch(1)
            rl.addWidget(QLabel(value), 0, Qt.AlignRight)

            setup_layout.addWidget(row)

        setup_layout.addStretch(1)
        left.add_widget(setup_scroll)
        body.addWidget(left, 2)

        # Центр
        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        metrics = PanelCard("Результат проверки", "Метрики должны быть понятны ещё до глубокого анализа.")
        metrics_grid_wrap = QWidget()
        metrics_grid_wrap.setProperty("transparentBg", True)
        grid = QGridLayout(metrics_grid_wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        for idx, metric in enumerate(self._vm.metrics):
            card = QFrame()
            card.setObjectName("PanelCardSoft")

            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(8)

            t = QLabel(metric.title)
            t.setObjectName("CardTitle")

            v = QLabel(metric.value)
            v.setObjectName("MetricValue")

            n = make_muted_label(metric.note)

            cl.addWidget(t)
            cl.addWidget(v)
            cl.addWidget(n)

            grid.addWidget(card, idx // 2, idx % 2)

        metrics.add_widget(metrics_grid_wrap)
        center.addWidget(metrics)

        # Проблемные кейсы
        cases = PanelCard("Проблемные кейсы", "Не только score, но и места, где нужно посмотреть руками.")
        case_scroll, case_layout = _stable_scroll_shell(340)

        for case in self._vm.problematic_cases:
            row = QFrame()
            row.setObjectName("PanelCardSoft")

            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(6)

            title = QLabel(case.title)
            title.setObjectName("CardTitle")

            rl.addWidget(title)
            rl.addWidget(make_muted_label(case.note))

            case_layout.addWidget(row)

        case_layout.addStretch(1)
        cases.add_widget(case_scroll)
        center.addWidget(cases, 1)

        # Правый блок: контекст результата
        right = PanelCard("Контекст результата", "Контекст помогает читать метрики правильно.")
        right_scroll, right_layout = _stable_scroll_shell(340, shell_margins=(0, 6, 0, 6), spacing=8)

        for item in self._vm.context_rows:
            row = QFrame()
            row.setProperty("transparentBg", True)

            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(0)

            pill = QLabel(item)
            pill.setObjectName("WorkflowPill")
            pill.setWordWrap(True)
            rl.addWidget(pill)

            right_layout.addWidget(row)

        right_layout.addStretch(1)
        right.add_widget(right_scroll)
        body.addWidget(right, 2)
