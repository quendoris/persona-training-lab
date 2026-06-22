from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel


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
    inner.setStyleSheet(
        """
        QWidget#AnalysisScrollWrap {
            background: transparent;
            border: none;
        }
        """
    )
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
        self._title = QLabel(self._vm.title)
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label(self._vm.subtitle)
        hl.addWidget(self._title)
        hl.addWidget(self._subtitle)
        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 5)

        self._compare = PanelCard("Портрет и устойчивость", "Анализ строится из реальных портретных тестов.")
        self._compare_grid = QGridLayout()
        self._compare_grid.setSpacing(12)
        self._compare_grid.setColumnStretch(0, 2)
        self._compare_grid.setColumnStretch(1, 1)
        self._compare_grid.setColumnStretch(2, 2)
        self._compare._layout.addLayout(self._compare_grid)
        center.addWidget(self._compare, 0)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        center.addLayout(lower, 1)

        insights = PanelCard("Ключевые выводы", "Что можно понять из последнего портретного запуска.")
        _scroll, self._insight_layout = _stable_scroll_list(280)
        insights.add_widget(_scroll)
        lower.addWidget(insights, 1)

        samples = PanelCard("Портретные кейсы", "Реальные промпты и ответы модели.")
        _sscroll, self._sample_layout = _stable_scroll_list(280)
        samples.add_widget(_sscroll)
        lower.addWidget(samples, 1)

        right = PanelCard("Дельта и риски", "Что делать с результатом дальше.")
        _scroll_r, self._delta_layout = _stable_scroll_list(280)
        right.add_widget(_scroll_r)
        body.addWidget(right, 2)

        self._refresh_all()

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._vm.refresh()
        self._refresh_all()
        super().showEvent(event)

    def _clear_layout(self, layout: QVBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh_header(self) -> None:
        self._title.setText(self._vm.title)
        self._subtitle.setText(self._vm.subtitle)

    def _refresh_compare(self) -> None:
        self._clear_layout(self._compare_grid)
        self._compare_grid.addWidget(
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
        self._compare_grid.addWidget(middle, 0, 1)

        self._compare_grid.addWidget(
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

    def _refresh_insights(self) -> None:
        self._clear_layout(self._insight_layout)
        shell = QFrame()
        shell.setObjectName("PanelCardSoft")
        shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        for text in self._vm.insights:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(4)
            rl.addWidget(make_muted_label(text))
            layout.addWidget(row)
        layout.addStretch(1)
        self._insight_layout.addWidget(shell, 1)

    def _refresh_samples(self) -> None:
        self._clear_layout(self._sample_layout)
        shell = QFrame()
        shell.setObjectName("PanelCardSoft")
        shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        for sample in self._vm.samples:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(6)
            title = QLabel(sample.title)
            title.setObjectName("CardTitle")
            rl.addWidget(title)
            rl.addWidget(make_muted_label(sample.left_note))
            rl.addWidget(make_muted_label(sample.right_note))
            layout.addWidget(row)
        layout.addStretch(1)
        self._sample_layout.addWidget(shell, 1)

    def _refresh_deltas(self) -> None:
        self._clear_layout(self._delta_layout)
        shell = QFrame()
        shell.setObjectName("PanelCardSoft")
        shell.setMinimumWidth(0)
        shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        for text in self._vm.deltas:
            layout.addWidget(_narrow_delta_row(text))
        layout.addStretch(1)
        self._delta_layout.addWidget(shell, 1)

    def _refresh_all(self) -> None:
        self._refresh_header()
        self._refresh_compare()
        self._refresh_insights()
        self._refresh_samples()
        self._refresh_deltas()
