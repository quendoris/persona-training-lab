from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.viewmodels.tests import TestsViewModel


def _stable_scroll_content(min_height: int = 340, max_height: int | None = None) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setMinimumHeight(min_height)
    if max_height is not None:
        scroll.setMaximumHeight(max_height)

    outer = QWidget()
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(10, 10, 10, 10)
    outer_layout.setSpacing(0)

    inner = QFrame()
    inner.setObjectName("StableScrollWrap")
    inner_layout = QVBoxLayout(inner)
    inner_layout.setContentsMargins(14, 14, 14, 14)
    inner_layout.setSpacing(12)
    outer_layout.addWidget(inner)
    scroll.setWidget(outer)
    return scroll, inner, inner_layout


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
        for i, text in enumerate(["Запустить проверку", "Открыть анализ", "Разобрать кейсы"]):
            btn = QPushButton(text)
            if i:
                btn.setObjectName("SecondaryButton")
            al.addWidget(btn)
        al.addStretch(1)
        root.addWidget(actions)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left = PanelCard("Контекст проверки", "Мы тестируем snapshot, а не training run напрямую.")
        setup_scroll, _setup_inner, setup_layout = _stable_scroll_content(360)
        for key, value in self._vm.setup_rows:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)
            rl.setSpacing(10)
            rl.addWidget(make_muted_label(key))
            rl.addStretch(1)
            rl.addWidget(QLabel(value), 0, Qt.AlignRight)
            setup_layout.addWidget(row)
        setup_layout.addStretch(1)
        left.add_widget(setup_scroll)
        body.addWidget(left, 2)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        metrics = PanelCard("Результат проверки", "Метрики должны быть понятны ещё до глубокого анализа.")
        grid = QGridLayout()
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
        metrics._layout.addLayout(grid)
        center.addWidget(metrics)

        cases = PanelCard("Проблемные кейсы", "Не только score, но и места, где нужно посмотреть руками.")
        case_scroll, _case_inner, case_layout = _stable_scroll_content(360)
        for case in self._vm.problematic_cases:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)
            rl.setSpacing(6)
            title = QLabel(case.title)
            title.setObjectName("CardTitle")
            rl.addWidget(title)
            rl.addWidget(make_muted_label(case.note))
            case_layout.addWidget(row)
        case_layout.addStretch(1)
        cases.add_widget(case_scroll)
        center.addWidget(cases, 1)

        right = PanelCard("Контекст результата", "Контекст помогает читать метрики правильно.")
        right_scroll, _right_inner, right_layout = _stable_scroll_content(360)
        for item in self._vm.context_rows:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)
            rl.addWidget(QLabel(item))
            right_layout.addWidget(row)
        right_layout.addStretch(1)
        right.add_widget(right_scroll)
        body.addWidget(right, 2)
