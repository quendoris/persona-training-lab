from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel

from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setWordWrap(False)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip(text)
        self._refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        width = max(24, self.contentsRect().width())
        elided = self.fontMetrics().elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            width,
        )
        super().setText(elided)


def _stable_scroll_list(min_height: int = 300) -> tuple[QScrollArea, QVBoxLayout]:
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
    outer_layout.setContentsMargins(10, 10, 10, 10)
    outer_layout.setSpacing(0)

    inner = QWidget()
    inner.setObjectName("AnalysisScrollWrap")
    inner.setStyleSheet("""
        QWidget#AnalysisScrollWrap {
            background: transparent;
            border: none;
        }
    """)

    layout = QVBoxLayout(inner)
    layout.setContentsMargins(0, 0, 0, 0)
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


def _pair_case_row(title: str, left_text: str, right_text: str) -> QFrame:
    row = QFrame()
    row.setObjectName("PanelCardSoft")

    rl = QVBoxLayout(row)
    rl.setContentsMargins(12, 10, 12, 10)
    rl.setSpacing(6)

    t = QLabel(title)
    t.setObjectName("CardTitle")
    rl.addWidget(t)
    rl.addWidget(make_muted_label("v2 · " + left_text))
    rl.addWidget(make_muted_label("v3 · " + right_text))
    return row


def _narrow_delta_row(text: str) -> QFrame:
    row = QFrame()
    row.setObjectName("PanelCardSoft")
    row.setMinimumWidth(0)
    row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    rl = QVBoxLayout(row)
    rl.setContentsMargins(12, 10, 12, 10)
    rl.setSpacing(4)

    label = QLabel(" ".join(text.split()))
    label.setObjectName("MutedText")
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    label.setTextInteractionFlags(Qt.NoTextInteraction)
    label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    rl.addWidget(label)
    return row


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

        compare_grid.addWidget(
            _summary_card(
                self._vm.left.title,
                self._vm.left.subtitle,
                self._vm.left.profile_match,
                self._vm.left.stability,
                self._vm.left.contradiction,
            ),
            0,
            0,
        )

        middle = QFrame()
        middle.setObjectName("PanelCardSoft")
        ml = QVBoxLayout(middle)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(10)

        for metric in self._vm.metrics:
            row = QFrame()
            row.setObjectName("AccentCard" if metric.delta.startswith("+") else "PanelCardSoft")
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

        compare_grid.addWidget(
            _summary_card(
                self._vm.right.title,
                self._vm.right.subtitle,
                self._vm.right.profile_match,
                self._vm.right.stability,
                self._vm.right.contradiction,
            ),
            0,
            2,
        )

        compare._layout.addLayout(compare_grid)
        center.addWidget(compare, 0)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        center.addLayout(lower, 1)

        insights = PanelCard("Ключевые выводы", "Помогает быстро понять, что именно изменилось.")
        scroll, insight_layout = _stable_scroll_list(280)

        insights_shell = QFrame()
        insights_shell.setObjectName("PanelCardSoft")
        insights_shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        insights_shell_layout = QVBoxLayout(insights_shell)
        insights_shell_layout.setContentsMargins(14, 14, 14, 14)
        insights_shell_layout.setSpacing(10)

        for text in self._vm.insights:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(4)
            rl.addWidget(make_muted_label(text))
            insights_shell_layout.addWidget(row)

        insights_shell_layout.addStretch(1)
        insight_layout.addWidget(insights_shell, 1)

        insights.add_widget(scroll)
        lower.addWidget(insights, 1)

        samples = PanelCard("Парные кейсы", "Compare должен помогать смотреть не только на метрики, но и на реальные ответы.")
        sscroll, sample_layout = _stable_scroll_list(280)

        samples_shell = QFrame()
        samples_shell.setObjectName("PanelCardSoft")
        samples_shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        samples_shell_layout = QVBoxLayout(samples_shell)
        samples_shell_layout.setContentsMargins(14, 14, 14, 14)
        samples_shell_layout.setSpacing(10)

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

            samples_shell_layout.addWidget(row)

        samples_shell_layout.addStretch(1)
        sample_layout.addWidget(samples_shell, 1)

        samples.add_widget(sscroll)
        lower.addWidget(samples, 1)

        right = PanelCard("Дельта и риски", "Краткая сводка того, что стало лучше и что ещё стоит проверить.")
        scroll_r, rows = _stable_scroll_list(280)

        delta_shell = QFrame()
        delta_shell.setObjectName("PanelCardSoft")
        delta_shell.setMinimumWidth(0)
        delta_shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        delta_shell_layout = QVBoxLayout(delta_shell)
        delta_shell_layout.setContentsMargins(14, 14, 14, 14)
        delta_shell_layout.setSpacing(10)

        for text in self._vm.deltas:
            delta_shell_layout.addWidget(_narrow_delta_row(text))

        delta_shell_layout.addStretch(1)
        rows.addWidget(delta_shell, 1)

        right.add_widget(scroll_r)
        body.addWidget(right, 2)
