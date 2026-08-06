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
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.analysis import (
    AnalysisViewModel,
    CompareSummary,
)
from persona_training_lab.ui.viewmodels.evaluation import EvaluationText


def _stable_scroll_list(
    min_height: int = 300,
) -> tuple[QScrollArea, QVBoxLayout]:
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


def _narrow_delta_row(text: str) -> QFrame:
    row = QFrame()
    row.setObjectName("PanelCardSoft")
    row.setMinimumWidth(0)
    row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    layout = QVBoxLayout(row)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)
    label = QLabel(" ".join(text.split()))
    label.setObjectName("MutedText")
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    label.setTextInteractionFlags(Qt.NoTextInteraction)
    label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    layout.addWidget(label)
    return row


class AnalysisScreen(QWidget):
    def __init__(
        self,
        view_model: AnalysisViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)
        self._title = QLabel()
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label("")
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 5)

        self._compare = PanelCard("", "")
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

        self._insights_card = PanelCard("", "")
        insight_scroll, self._insight_layout = _stable_scroll_list(280)
        self._insights_card.add_widget(insight_scroll)
        lower.addWidget(self._insights_card, 1)

        self._samples_card = PanelCard("", "")
        sample_scroll, self._sample_layout = _stable_scroll_list(280)
        self._samples_card.add_widget(sample_scroll)
        lower.addWidget(self._samples_card, 1)

        self._delta_card = PanelCard("", "")
        delta_scroll, self._delta_layout = _stable_scroll_list(280)
        self._delta_card.add_widget(delta_scroll)
        body.addWidget(self._delta_card, 2)

        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _render(self, value: str | EvaluationText | object) -> str:
        if not isinstance(value, EvaluationText):
            return str(value)
        values = {
            key: self._render(item)
            for key, item in value.values.items()
        }
        return self._text(value.key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self._compare.set_title(
            self._text("analysis.card.compare.title")
        )
        self._compare.set_subtitle(
            self._text("analysis.card.compare.subtitle")
        )
        self._insights_card.set_title(
            self._text("analysis.card.insights.title")
        )
        self._insights_card.set_subtitle(
            self._text("analysis.card.insights.subtitle")
        )
        self._samples_card.set_title(
            self._text("analysis.card.samples.title")
        )
        self._samples_card.set_subtitle(
            self._text("analysis.card.samples.subtitle")
        )
        self._delta_card.set_title(
            self._text("analysis.card.delta.title")
        )
        self._delta_card.set_subtitle(
            self._text("analysis.card.delta.subtitle")
        )
        self._refresh_all()

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._vm.refresh()
        self._refresh_all()
        super().showEvent(event)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh_header(self) -> None:
        self._title.setText(self._render(self._vm.header_title_model()))
        self._subtitle.setText(
            self._render(self._vm.header_subtitle_model())
        )

    def _summary_card(self, summary: CompareSummary) -> QFrame:
        card = QFrame()
        card.setObjectName("PanelCardSoft")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(
            self._render(self._vm.summary_title_model(summary))
        )
        title.setObjectName("CardTitle")
        layout.addWidget(title)
        layout.addWidget(
            make_muted_label(
                self._render(self._vm.summary_subtitle_model(summary))
            )
        )

        metrics_wrap = QFrame()
        metrics_wrap.setObjectName("StableScrollWrap")
        metrics_layout = QVBoxLayout(metrics_wrap)
        metrics_layout.setContentsMargins(12, 12, 12, 12)
        metrics_layout.setSpacing(10)

        rows = (
            (
                self._text("analysis.summary.metric.match"),
                summary.profile_match,
            ),
            (
                self._text("analysis.summary.metric.stability"),
                self._render(
                    self._vm.summary_stability_model(summary)
                ),
            ),
            (
                self._text("analysis.summary.metric.contradictions"),
                summary.contradiction,
            ),
        )
        for key, value in rows:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(10)
            row_layout.addWidget(make_muted_label(key))
            row_layout.addStretch(1)
            value_label = QLabel(value)
            value_label.setObjectName("MetricPercentPill")
            value_label.setAlignment(Qt.AlignCenter)
            row_layout.addWidget(value_label, 0, Qt.AlignRight)
            metrics_layout.addWidget(row)

        layout.addWidget(metrics_wrap)
        return card

    def _refresh_compare(self) -> None:
        self._clear_layout(self._compare_grid)
        self._compare_grid.addWidget(
            self._summary_card(self._vm.left),
            0,
            0,
        )

        middle = QFrame()
        middle.setObjectName("PanelCardSoft")
        middle_layout = QVBoxLayout(middle)
        middle_layout.setContentsMargins(14, 12, 14, 12)
        middle_layout.setSpacing(10)
        for metric in self._vm.metrics:
            row = QFrame()
            row.setObjectName(
                "AccentCard"
                if metric.delta.startswith("+")
                else "PanelCardSoft"
            )
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(4)
            label = QLabel(
                self._render(self._vm.metric_title_model(metric))
            )
            label.setObjectName("CardTitle")
            value = QLabel(metric.delta)
            value.setObjectName("MetricValue")
            value.setMaximumHeight(42)
            row_layout.addWidget(label)
            row_layout.addWidget(value)
            row_layout.addWidget(
                make_muted_label(
                    self._render(self._vm.metric_note_model(metric))
                )
            )
            middle_layout.addWidget(row)
        self._compare_grid.addWidget(middle, 0, 1)

        self._compare_grid.addWidget(
            self._summary_card(self._vm.right),
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
        for item in self._vm.insight_models():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(4)
            row_layout.addWidget(make_muted_label(self._render(item)))
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
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(6)
            title = QLabel(
                self._render(self._vm.sample_title_model(sample))
            )
            title.setObjectName("CardTitle")
            row_layout.addWidget(title)
            row_layout.addWidget(
                make_muted_label(
                    "\n".join(
                        self._render(item)
                        for item in self._vm.sample_left_models(sample)
                    )
                )
            )
            row_layout.addWidget(
                make_muted_label(
                    "\n".join(
                        self._render(item)
                        for item in self._vm.sample_right_models(sample)
                    )
                )
            )
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
        for item in self._vm.delta_models():
            layout.addWidget(_narrow_delta_row(self._render(item)))
        layout.addStretch(1)
        self._delta_layout.addWidget(shell, 1)

    def _refresh_all(self) -> None:
        self._refresh_header()
        self._refresh_compare()
        self._refresh_insights()
        self._refresh_samples()
        self._refresh_deltas()
