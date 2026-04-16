from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel


def _stable_scroll_list(min_height: int = 300) -> tuple[QScrollArea, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setMinimumHeight(min_height)

    outer = QWidget()
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(10, 10, 10, 10)
    outer_layout.setSpacing(0)

    inner = QFrame()
    inner.setObjectName("StableScrollWrap")
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(12)
    outer_layout.addWidget(inner)
    scroll.setWidget(outer)
    return scroll, layout


def _summary_card(title: str, subtitle: str, profile_match: str, stability: str, contradiction: str) -> QFrame:
    card = QFrame()
    card.setObjectName("PanelCardSoft")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    head = QLabel(title)
    head.setObjectName("CardTitle")
    layout.addWidget(head)
    layout.addWidget(make_muted_label(subtitle))

    metrics_wrap = QFrame()
    metrics_wrap.setObjectName("StableScrollWrap")
    metrics_layout = QVBoxLayout(metrics_wrap)
    metrics_layout.setContentsMargins(12, 12, 12, 12)
    metrics_layout.setSpacing(10)
    for key, value in [("Совпадение", profile_match), ("Стабильность", stability), ("Противоречия", contradiction)]:
        row = QFrame()
        row.setObjectName("PanelCardSoft")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(10, 8, 10, 8)
        rl.setSpacing(10)
        rl.addWidget(make_muted_label(key))
        rl.addStretch(1)
        value_lbl = QLabel(value)
        value_lbl.setObjectName("MetricPercentPill")
        value_lbl.setAlignment(Qt.AlignCenter)
        rl.addWidget(value_lbl, 0, Qt.AlignRight)
        metrics_layout.addWidget(row)
    layout.addWidget(metrics_wrap)
    return card


class AnalysisScreen(QWidget):
    def __init__(self, view_model: AnalysisViewModel) -> None:
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

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 5)

        compare = PanelCard("Сравнение версий", "Слева и справа — не просто объекты, а основания для решения.")
        compare_grid = QGridLayout()
        compare_grid.setSpacing(12)
        compare_grid.setColumnStretch(0, 2)
        compare_grid.setColumnStretch(1, 1)
        compare_grid.setColumnStretch(2, 2)
        compare_grid.addWidget(_summary_card(
            self._vm.left.title, self._vm.left.subtitle, self._vm.left.profile_match, self._vm.left.stability, self._vm.left.contradiction
        ), 0, 0)

        middle = QFrame()
        middle.setObjectName("PanelCardSoft")
        ml = QVBoxLayout(middle)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(10)
        for metric in self._vm.metrics:
            row = QFrame()
            row.setObjectName("AccentCard" if metric.delta.startswith('+') else "PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(4)
            lbl = QLabel(metric.title)
            lbl.setObjectName("CardTitle")
            value = QLabel(metric.delta)
            value.setObjectName("MetricValue")
            value.setMaximumHeight(42)
            rl.addWidget(lbl)
            rl.addWidget(value)
            rl.addWidget(make_muted_label(metric.note))
            ml.addWidget(row)
        compare_grid.addWidget(middle, 0, 1)
        compare_grid.addWidget(_summary_card(
            self._vm.right.title, self._vm.right.subtitle, self._vm.right.profile_match, self._vm.right.stability, self._vm.right.contradiction
        ), 0, 2)
        compare._layout.addLayout(compare_grid)
        center.addWidget(compare, 0)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        center.addLayout(lower, 1)

        insights = PanelCard("Ключевые выводы", "Помогает быстро понять, что именно изменилось.")
        scroll, insight_layout = _stable_scroll_list(280)
        for text in self._vm.insights:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.addWidget(make_muted_label(text))
            insight_layout.addWidget(row)
        insight_layout.addStretch(1)
        insights.add_widget(scroll)
        lower.addWidget(insights, 1)

        samples = PanelCard("Парные кейсы", "Compare должен помогать смотреть не только на метрики, но и на реальные ответы.")
        sscroll, sample_layout = _stable_scroll_list(280)
        for sample in self._vm.samples:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(6)
            t = QLabel(sample.title)
            t.setObjectName("CardTitle")
            rl.addWidget(t)
            rl.addWidget(make_muted_label("v2 · " + sample.left_note))
            rl.addWidget(make_muted_label("v3 · " + sample.right_note))
            sample_layout.addWidget(row)
        sample_layout.addStretch(1)
        samples.add_widget(sscroll)
        lower.addWidget(samples, 1)

        right = PanelCard("Дельта и риски", "Краткая сводка того, что стало лучше и что ещё стоит проверить.")
        scroll_r, rows = _stable_scroll_list(280)
        for text in self._vm.deltas:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.addWidget(QLabel(text))
            rows.addWidget(row)
        rows.addStretch(1)
        right.add_widget(scroll_r)
        body.addWidget(right, 2)
