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

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.tests import TestsViewModel


class _TestsWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, vm: TestsViewModel) -> None:
        super().__init__()
        self._vm = vm

    def run(self) -> None:
        ok, message = self._vm.run_tests_sync()
        self.finished.emit(ok, message)


class _CasesDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Разбор портретных кейсов")
        self.resize(920, 640)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Психологический портрет модели")
        title.setObjectName("ScreenTitle")
        layout.addWidget(title)
        layout.addWidget(make_muted_label("Здесь показаны реальные ответы модели по измерениям личности. Авторазметка смысла пока не выполняется."))

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self._text, 1)

        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    def set_text(self, text: str) -> None:
        self._text.setPlainText(text)


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
    open_analysis_requested = Signal()

    def __init__(self, view_model: TestsViewModel) -> None:
        super().__init__()
        self._vm = view_model
        self._tests_thread: QThread | None = None
        self._tests_worker: _TestsWorker | None = None
        self._cases_dialog: _CasesDialog | None = None

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

        actions = QFrame()
        actions.setObjectName("PanelCardSoft")
        al = QHBoxLayout(actions)
        al.setContentsMargins(18, 14, 18, 14)
        al.setSpacing(10)

        self._run_btn = QPushButton("Собрать портрет")
        self._run_btn.clicked.connect(self._on_run_tests)
        al.addWidget(self._run_btn)

        self._open_analysis_btn = QPushButton("Открыть анализ")
        self._open_analysis_btn.setObjectName("SecondaryButton")
        self._open_analysis_btn.setToolTip("Перейти во вкладку анализа результатов портретного теста")
        self._open_analysis_btn.clicked.connect(self.open_analysis_requested.emit)
        al.addWidget(self._open_analysis_btn)

        self._review_cases_btn = QPushButton("Разобрать кейсы")
        self._review_cases_btn.setObjectName("SecondaryButton")
        self._review_cases_btn.setToolTip("Открыть полный разбор промптов и ответов модели")
        self._review_cases_btn.clicked.connect(self._on_review_cases)
        al.addWidget(self._review_cases_btn)

        al.addStretch(1)
        root.addWidget(actions)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left = PanelCard("Контекст проверки", "Портретный тест устойчивости личности модели.")
        self._setup_scroll, self._setup_layout = _stable_scroll_shell(340)
        left.add_widget(self._setup_scroll)
        body.addWidget(left, 2)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        metrics = PanelCard("Результат портрета", "Метрики показывают факт запуска и полноту ответов по измерениям.")
        metrics_grid_wrap = QWidget()
        metrics_grid_wrap.setProperty("transparentBg", True)
        self._metrics_grid = QGridLayout(metrics_grid_wrap)
        self._metrics_grid.setContentsMargins(0, 0, 0, 0)
        self._metrics_grid.setSpacing(12)
        metrics.add_widget(metrics_grid_wrap)
        center.addWidget(metrics)

        cases = PanelCard("Портретные кейсы", "Реальные ответы модели по измерениям личности.")
        self._case_scroll, self._case_layout = _stable_scroll_shell(340)
        cases.add_widget(self._case_scroll)
        center.addWidget(cases, 1)

        right = PanelCard("Контекст результата", "Контекст помогает читать портрет без псевдодиагностики.")
        self._right_scroll, self._right_layout = _stable_scroll_shell(340, shell_margins=(0, 6, 0, 6), spacing=8)
        right.add_widget(self._right_scroll)
        body.addWidget(right, 2)
        self._refresh_all()

    def _clear_layout(self, layout: QVBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh_header(self) -> None:
        self._title.setText(self._vm.title)
        self._subtitle.setText(self._vm.subtitle)
        self._run_btn.setEnabled(not self._vm.run_in_progress)
        self._run_btn.setText("Выполняется…" if self._vm.run_in_progress else "Собрать портрет")
        self._open_analysis_btn.setEnabled(not self._vm.run_in_progress)
        self._review_cases_btn.setEnabled(not self._vm.run_in_progress)

    def _refresh_setup(self) -> None:
        self._clear_layout(self._setup_layout)
        for key, value in self._vm.setup_rows:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(10)
            rl.addWidget(make_muted_label(key))
            rl.addStretch(1)
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            rl.addWidget(value_label, 0, Qt.AlignRight)
            self._setup_layout.addWidget(row)
        self._setup_layout.addStretch(1)

    def _refresh_metrics(self) -> None:
        self._clear_layout(self._metrics_grid)
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
            self._metrics_grid.addWidget(card, idx // 2, idx % 2)

    def _refresh_cases(self) -> None:
        self._clear_layout(self._case_layout)
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
            self._case_layout.addWidget(row)
        self._case_layout.addStretch(1)

    def _refresh_context(self) -> None:
        self._clear_layout(self._right_layout)
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
        self._tests_worker.finished.connect(self._tests_worker.deleteLater)
        self._tests_thread.finished.connect(self._tests_thread.deleteLater)
        self._tests_thread.finished.connect(self._clear_worker_refs)
        self._tests_thread.start()

    def _on_tests_finished(self, ok: bool, message: str) -> None:
        self._vm.finish_run(ok, message)
        self._refresh_all()
        if self._cases_dialog is not None and self._cases_dialog.isVisible():
            self._cases_dialog.set_text(self._vm.review_text())

    def _on_review_cases(self) -> None:
        if self._cases_dialog is None:
            self._cases_dialog = _CasesDialog(self)
        self._cases_dialog.set_text(self._vm.review_text())
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
