from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.application.experiments.service import (
    ExperimentRunResult,
)
from persona_training_lab.application.experiments.status_mapping import (
    normalize_evaluation_status,
)
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.evaluation import (
    EvaluationText,
    evaluation_status_text,
)
from persona_training_lab.ui.viewmodels.tests import (
    EvaluationMetric,
    TestsViewModel,
)


class _TestsWorker(QObject):
    finished = Signal(object)

    def __init__(self, vm: TestsViewModel) -> None:
        super().__init__()
        self._vm = vm

    def run(self) -> None:
        self.finished.emit(self._vm.run_tests_sync())


class _CasesDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__(parent)
        self._localization = localization
        self._models: tuple[str | EvaluationText, ...] = ()
        self.resize(920, 640)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._title = QLabel()
        self._title.setObjectName("ScreenTitle")
        layout.addWidget(self._title)
        self._subtitle = make_muted_label("")
        layout.addWidget(self._subtitle)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self._text, 1)

        self._close_btn = QPushButton()
        self._close_btn.setObjectName("SecondaryButton")
        self._close_btn.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self._close_btn)
        layout.addLayout(footer)

        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text_value(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _render(self, value: str | EvaluationText | object) -> str:
        if not isinstance(value, EvaluationText):
            return str(value)
        values = {
            key: self._render(item)
            for key, item in value.values.items()
        }
        return self._text_value(value.key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self.setWindowTitle(self._text_value("tests.dialog.cases.title"))
        self._title.setText(self._text_value("tests.dialog.cases.header"))
        self._subtitle.setText(
            self._text_value("tests.dialog.cases.subtitle")
        )
        self._close_btn.setText(self._text_value("common.close"))
        self._text.setPlainText(
            "\n".join(self._render(item) for item in self._models)
        )

    def set_models(
        self,
        models: tuple[str | EvaluationText, ...],
    ) -> None:
        self._models = models
        self._apply_language()


def _stable_scroll_shell(
    min_height: int = 340,
    *,
    shell_margins: tuple[int, int, int, int] = (14, 14, 14, 14),
    spacing: int = 10,
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
    open_analysis_requested = Signal()

    def __init__(
        self,
        view_model: TestsViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization
        self._tests_thread: QThread | None = None
        self._tests_worker: _TestsWorker | None = None
        self._cases_dialog: _CasesDialog | None = None

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

        actions = QFrame()
        actions.setObjectName("PanelCardSoft")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(18, 14, 18, 14)
        actions_layout.setSpacing(10)

        self._run_btn = QPushButton()
        self._run_btn.clicked.connect(self._on_run_tests)
        actions_layout.addWidget(self._run_btn)

        self._open_analysis_btn = QPushButton()
        self._open_analysis_btn.setObjectName("SecondaryButton")
        self._open_analysis_btn.clicked.connect(
            self.open_analysis_requested.emit
        )
        actions_layout.addWidget(self._open_analysis_btn)

        self._review_cases_btn = QPushButton()
        self._review_cases_btn.setObjectName("SecondaryButton")
        self._review_cases_btn.clicked.connect(self._on_review_cases)
        actions_layout.addWidget(self._review_cases_btn)

        actions_layout.addStretch(1)
        root.addWidget(actions)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        self._setup_card = PanelCard("", "")
        self._setup_scroll, self._setup_layout = _stable_scroll_shell(340)
        self._setup_card.add_widget(self._setup_scroll)
        body.addWidget(self._setup_card, 2)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        self._metrics_card = PanelCard("", "")
        metrics_grid_wrap = QWidget()
        metrics_grid_wrap.setProperty("transparentBg", True)
        self._metrics_grid = QGridLayout(metrics_grid_wrap)
        self._metrics_grid.setContentsMargins(0, 0, 0, 0)
        self._metrics_grid.setSpacing(12)
        self._metrics_card.add_widget(metrics_grid_wrap)
        center.addWidget(self._metrics_card)

        self._cases_card = PanelCard("", "")
        self._case_scroll, self._case_layout = _stable_scroll_shell(340)
        self._cases_card.add_widget(self._case_scroll)
        center.addWidget(self._cases_card, 1)

        self._context_card = PanelCard("", "")
        self._right_scroll, self._right_layout = _stable_scroll_shell(
            340,
            shell_margins=(0, 6, 0, 6),
            spacing=8,
        )
        self._context_card.add_widget(self._right_scroll)
        body.addWidget(self._context_card, 2)

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

    @staticmethod
    def _clear_layout(layout: QVBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _apply_language(self, _locale: str = "") -> None:
        self._open_analysis_btn.setText(
            self._text("tests.action.open_analysis")
        )
        self._open_analysis_btn.setToolTip(
            self._text("tests.action.open_analysis.tooltip")
        )
        self._review_cases_btn.setText(
            self._text("tests.action.review")
        )
        self._review_cases_btn.setToolTip(
            self._text("tests.action.review.tooltip")
        )
        self._setup_card.set_title(self._text("tests.card.setup.title"))
        self._setup_card.set_subtitle(
            self._text("tests.card.setup.subtitle")
        )
        self._metrics_card.set_title(
            self._text("tests.card.metrics.title")
        )
        self._metrics_card.set_subtitle(
            self._text("tests.card.metrics.subtitle")
        )
        self._cases_card.set_title(self._text("tests.card.cases.title"))
        self._cases_card.set_subtitle(
            self._text("tests.card.cases.subtitle")
        )
        self._context_card.set_title(
            self._text("tests.card.context.title")
        )
        self._context_card.set_subtitle(
            self._text("tests.card.context.subtitle")
        )
        self._refresh_all()
        if self._cases_dialog is not None:
            self._cases_dialog.set_models(self._vm.review_models())

    def _refresh_header(self) -> None:
        self._title.setText(self._render(self._vm.header_title_model()))
        self._subtitle.setText(
            self._render(self._vm.header_subtitle_model())
        )
        self._run_btn.setEnabled(not self._vm.run_in_progress)
        self._run_btn.setText(
            self._text("tests.action.running")
            if self._vm.run_in_progress
            else self._text("tests.action.run")
        )
        self._open_analysis_btn.setEnabled(not self._vm.run_in_progress)
        self._review_cases_btn.setEnabled(not self._vm.run_in_progress)

    def _refresh_setup(self) -> None:
        self._clear_layout(self._setup_layout)
        for key, value in self._vm.setup_models():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(10)
            layout.addWidget(make_muted_label(self._render(key)))
            layout.addStretch(1)
            value_label = QLabel(self._render(value))
            value_label.setWordWrap(True)
            layout.addWidget(value_label, 0, Qt.AlignRight)
            self._setup_layout.addWidget(row)
        self._setup_layout.addStretch(1)

    def _metric_value(self, metric: EvaluationMetric) -> str:
        title_model = metric.title_model
        if (
            isinstance(title_model, EvaluationText)
            and title_model.key == "tests.metric.latest_status"
        ):
            return self._render(
                evaluation_status_text(
                    normalize_evaluation_status(metric.value),
                    metric.value,
                )
            )
        return metric.value

    def _refresh_metrics(self) -> None:
        self._clear_layout(self._metrics_grid)
        for index, metric in enumerate(self._vm.metrics):
            card = QFrame()
            card.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(8)
            title = QLabel(
                self._render(self._vm.metric_title_model(metric))
            )
            title.setObjectName("CardTitle")
            value = QLabel(self._metric_value(metric))
            value.setObjectName("MetricValue")
            note = make_muted_label(
                self._render(self._vm.metric_note_model(metric))
            )
            layout.addWidget(title)
            layout.addWidget(value)
            layout.addWidget(note)
            self._metrics_grid.addWidget(
                card,
                index // 2,
                index % 2,
            )

    def _refresh_cases(self) -> None:
        self._clear_layout(self._case_layout)
        for case in self._vm.problematic_cases:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(6)
            title = QLabel(
                self._render(self._vm.case_title_model(case))
            )
            title.setObjectName("CardTitle")
            layout.addWidget(title)
            note = "\n".join(
                self._render(item)
                for item in self._vm.case_note_models(case)
            )
            layout.addWidget(make_muted_label(note))
            self._case_layout.addWidget(row)
        self._case_layout.addStretch(1)

    def _refresh_context(self) -> None:
        self._clear_layout(self._right_layout)
        for item in self._vm.context_models():
            row = QFrame()
            row.setProperty("transparentBg", True)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            pill = QLabel(self._render(item))
            pill.setObjectName("WorkflowPill")
            pill.setWordWrap(True)
            layout.addWidget(pill)
            self._right_layout.addWidget(row)
        self._right_layout.addStretch(1)

    def _refresh_all(self) -> None:
        self._refresh_header()
        self._refresh_setup()
        self._refresh_metrics()
        self._refresh_cases()
        self._refresh_context()

    def _on_run_tests(self) -> None:
        if not self._vm.begin_run():
            return
        self._refresh_all()
        self._tests_thread = QThread(self)
        self._tests_worker = _TestsWorker(self._vm)
        self._tests_worker.moveToThread(self._tests_thread)
        self._tests_thread.started.connect(self._tests_worker.run)
        self._tests_worker.finished.connect(self._on_tests_finished)
        self._tests_worker.finished.connect(self._tests_thread.quit)
        self._tests_worker.finished.connect(
            self._tests_worker.deleteLater
        )
        self._tests_thread.finished.connect(
            self._tests_thread.deleteLater
        )
        self._tests_thread.finished.connect(self._clear_worker_refs)
        self._tests_thread.start()

    def _on_tests_finished(self, result: ExperimentRunResult) -> None:
        self._vm.finish_run(result)
        self._refresh_all()
        if self._cases_dialog is not None and self._cases_dialog.isVisible():
            self._cases_dialog.set_models(self._vm.review_models())

    def _on_review_cases(self) -> None:
        if self._cases_dialog is None:
            self._cases_dialog = _CasesDialog(
                self,
                self._localization,
            )
        self._cases_dialog.set_models(self._vm.review_models())
        self._cases_dialog.show()
        self._cases_dialog.raise_()
        self._cases_dialog.activateWindow()

    def _clear_worker_refs(self) -> None:
        self._tests_thread = None
        self._tests_worker = None

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._cases_dialog is not None:
            self._cases_dialog.close()
        if self._tests_thread is not None and self._tests_thread.isRunning():
            self._tests_thread.quit()
            self._tests_thread.wait(2000)
        super().closeEvent(event)
