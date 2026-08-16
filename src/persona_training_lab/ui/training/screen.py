from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.metrics import RoundedMetricBar
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.training import (
    TrainingText,
    TrainingViewModel,
)


class _InferenceWorker(QObject):
    finished = Signal(str, str)

    def __init__(self, vm: TrainingViewModel, prompt: str) -> None:
        super().__init__()
        self._vm = vm
        self._prompt = prompt

    def run(self) -> None:
        status, response = self._vm.run_local_inference_sync(self._prompt)
        self.finished.emit(status, response)


class _TrainingWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, vm: TrainingViewModel) -> None:
        super().__init__()
        self._vm = vm

    def run(self) -> None:
        ok, message = self._vm.start_selected_training_run()
        self.finished.emit(ok, message)


class _TrainingLogsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__(parent)
        self._localization = localization
        self._logs: tuple[str, ...] = ()
        self.resize(860, 560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._header = QLabel()
        self._header.setObjectName("ScreenTitle")
        layout.addWidget(self._header)

        self._box = QTextEdit()
        self._box.setReadOnly(True)
        self._box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._box, 1)

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

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self.setWindowTitle(self._text("training.dialog.logs.title"))
        self._header.setText(self._text("training.dialog.logs.header"))
        self._close_btn.setText(self._text("common.close"))
        self._box.setPlainText("\n".join(self._logs))

    def set_logs(self, logs: tuple[str, ...]) -> None:
        self._logs = logs
        self._box.setPlainText("\n".join(logs))
        cursor = self._box.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._box.setTextCursor(cursor)


class TrainingScreen(QWidget):
    def __init__(
        self,
        view_model: TrainingViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization
        self._logs_dialog: _TrainingLogsDialog | None = None
        self._inference_thread: QThread | None = None
        self._inference_worker: _InferenceWorker | None = None
        self._training_thread: QThread | None = None
        self._training_worker: _TrainingWorker | None = None

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
        actions_layout.setContentsMargins(18, 16, 18, 16)
        actions_layout.setSpacing(12)
        self._status_label = make_status_label("")
        actions_layout.addWidget(self._status_label)

        self._pause_btn = QPushButton()
        self._pause_btn.setObjectName("SecondaryButton")
        self._pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pause_btn.setMinimumHeight(34)
        self._pause_btn.setEnabled(False)
        actions_layout.addWidget(self._pause_btn)

        self._stop_btn = QPushButton()
        self._stop_btn.setObjectName("SecondaryButton")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setMinimumHeight(34)
        self._stop_btn.setEnabled(False)
        actions_layout.addWidget(self._stop_btn)

        self._open_logs_btn = QPushButton()
        self._open_logs_btn.setObjectName("SecondaryButton")
        self._open_logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_logs_btn.setMinimumHeight(34)
        self._open_logs_btn.clicked.connect(self._on_open_logs)
        actions_layout.addWidget(self._open_logs_btn)

        self._launch_btn = QPushButton()
        self._launch_btn.clicked.connect(self._on_start_training)
        actions_layout.addWidget(self._launch_btn)
        actions_layout.addStretch(1)
        root.addWidget(actions)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left = QVBoxLayout()
        left.setSpacing(16)
        body.addLayout(left, 4)

        self._overview_card = PanelCard("", "")
        self._stat_grid = QGridLayout()
        self._stat_grid.setSpacing(12)
        self._overview_card._layout.addLayout(self._stat_grid)
        self._progress_bar = RoundedMetricBar(0, height=14)
        progress_wrap = QVBoxLayout()
        progress_wrap.setSpacing(8)
        progress_wrap.addWidget(self._progress_bar)
        self._progress_chip = QLabel()
        self._progress_chip.setObjectName("TelemetryChip")
        progress_wrap.addWidget(
            self._progress_chip,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        self._overview_card._layout.addLayout(progress_wrap)
        left.addWidget(self._overview_card)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        left.addLayout(lower, 1)

        self._checkpoints_card = PanelCard("", "")
        cp_scroll = QScrollArea()
        cp_scroll.setObjectName("StableScrollArea")
        cp_scroll.setWidgetResizable(True)
        cp_scroll.setFrameShape(QFrame.Shape.NoFrame)
        cp_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        cp_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        cp_scroll.setMinimumHeight(250)
        apply_scrollbar_style(cp_scroll)

        cp_outer = QFrame()
        cp_outer.setObjectName("CheckpointScrollShell")
        cp_outer_layout = QVBoxLayout(cp_outer)
        cp_outer_layout.setContentsMargins(14, 14, 14, 14)
        cp_outer_layout.setSpacing(0)

        cp_wrap = QWidget()
        cp_wrap.setObjectName("CheckpointScrollWrap")
        cp_wrap.setStyleSheet(
            """
            QWidget#CheckpointScrollWrap {
                background: transparent;
                border: none;
            }
            """
        )
        self._checkpoint_layout = QVBoxLayout(cp_wrap)
        self._checkpoint_layout.setContentsMargins(0, 0, 0, 0)
        self._checkpoint_layout.setSpacing(10)
        cp_outer_layout.addWidget(cp_wrap)
        cp_scroll.setWidget(cp_outer)
        self._checkpoints_card.add_widget(cp_scroll)
        lower.addWidget(self._checkpoints_card, 1)

        self._logs_card = PanelCard("", "")
        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._logs_card.add_widget(self._log_box)
        lower.addWidget(self._logs_card, 1)

        right = QVBoxLayout()
        right.setSpacing(16)
        body.addLayout(right, 2)

        self._create_run_card = PanelCard("", "")
        create_layout = QGridLayout()
        create_layout.setHorizontalSpacing(8)
        create_layout.setVerticalSpacing(8)

        self._run_name = QLineEdit()
        self._profile_combo = QComboBox()
        self._dataset_combo = QComboBox()
        self._model_name = QLineEdit(self._vm.local_model_name)
        self._epochs = QSpinBox()
        self._epochs.setRange(1, 10000)
        self._epochs.setValue(3)
        self._batch_size = QSpinBox()
        self._batch_size.setRange(1, 100000)
        self._batch_size.setValue(4)
        self._learning_rate = QDoubleSpinBox()
        self._learning_rate.setDecimals(6)
        self._learning_rate.setRange(0.000001, 1.0)
        self._learning_rate.setSingleStep(0.0001)
        self._learning_rate.setValue(0.0002)

        fields = (
            ("training.field.run_name", self._run_name),
            ("training.field.profile", self._profile_combo),
            ("training.field.dataset", self._dataset_combo),
            ("training.field.model", self._model_name),
            ("training.field.epochs", self._epochs),
            ("training.field.batch_size", self._batch_size),
            ("training.field.learning_rate", self._learning_rate),
        )
        self._create_field_labels: list[tuple[QLabel, str]] = []
        for row, (key, widget) in enumerate(fields):
            label = make_muted_label("")
            self._create_field_labels.append((label, key))
            create_layout.addWidget(label, row, 0)
            create_layout.addWidget(widget, row, 1)

        self._create_run_btn = QPushButton()
        self._create_run_btn.setObjectName("SecondaryButton")
        self._create_run_btn.clicked.connect(self._on_create_run)
        create_layout.addWidget(self._create_run_btn, 7, 0, 1, 2)

        self._create_message = make_muted_label("")
        create_layout.addWidget(self._create_message, 8, 0, 1, 2)
        self._artifact_path = make_muted_label("")
        create_layout.addWidget(self._artifact_path, 9, 0, 1, 2)
        self._create_run_card._layout.addLayout(create_layout)
        right.addWidget(self._create_run_card)

        self._local_model_card = PanelCard("", "")
        local_rows = QVBoxLayout()
        local_rows.setSpacing(10)

        model_row = QFrame()
        model_row.setObjectName("PanelCardSoft")
        model_layout = QHBoxLayout(model_row)
        model_layout.setContentsMargins(12, 10, 12, 10)
        model_layout.setSpacing(10)
        self._model_label = make_muted_label("")
        model_layout.addWidget(self._model_label)
        model_layout.addStretch(1)
        self._model_value = QLabel(self._vm.local_model_name)
        model_layout.addWidget(
            self._model_value,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        local_rows.addWidget(model_row)

        path_row = QFrame()
        path_row.setObjectName("PanelCardSoft")
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(12, 10, 12, 10)
        path_layout.setSpacing(10)
        self._path_label = make_muted_label("")
        path_layout.addWidget(self._path_label)
        path_layout.addStretch(1)
        self._path_value = QLabel(self._vm.local_model_path)
        path_layout.addWidget(
            self._path_value,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        local_rows.addWidget(path_row)

        self._local_model_status = make_status_label("")
        local_rows.addWidget(self._local_model_status)
        self._local_model_note = make_muted_label("")
        local_rows.addWidget(self._local_model_note)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self._check_model_btn = QPushButton()
        self._check_model_btn.setObjectName("SecondaryButton")
        self._check_model_btn.clicked.connect(self._on_check_local_model)
        controls.addWidget(self._check_model_btn)
        self._test_inference_btn = QPushButton()
        self._test_inference_btn.setObjectName("SecondaryButton")
        self._test_inference_btn.clicked.connect(self._on_test_inference)
        controls.addWidget(self._test_inference_btn)
        controls.addStretch(1)
        local_rows.addLayout(controls)

        self._inference_prompt = QLineEdit(self._vm.inference_prompt)
        local_rows.addWidget(self._inference_prompt)
        self._local_inference_note = make_muted_label("")
        local_rows.addWidget(self._local_inference_note)
        self._local_inference_output = QTextEdit()
        self._local_inference_output.setReadOnly(True)
        self._local_inference_output.setMaximumHeight(84)
        local_rows.addWidget(self._local_inference_output)

        self._local_model_card._layout.addLayout(local_rows)
        right.addWidget(self._local_model_card)
        right.addStretch(1)

        self._runner_timer = QTimer(self)
        self._runner_timer.setInterval(600)
        self._runner_timer.timeout.connect(self._on_runner_tick)

        self._apply_static_text()
        self._populate_training_inputs()
        self._refresh_training_overview()
        self._refresh_local_model_block()
        if localization is not None:
            localization.language_changed.connect(self._refresh_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _render(self, value: object) -> str:
        if isinstance(value, TrainingText):
            rendered_values = {
                key: self._render(item)
                if isinstance(item, TrainingText)
                else item
                for key, item in value.values.items()
            }
            return self._text(value.key, **rendered_values)
        return str(value)

    def _apply_static_text(self) -> None:
        self._pause_btn.setText(self._text("training.action.pause"))
        self._pause_btn.setToolTip(
            self._text("training.tooltip.pause_unavailable")
        )
        self._stop_btn.setText(self._text("training.action.stop"))
        self._stop_btn.setToolTip(
            self._text("training.tooltip.stop_unavailable")
        )
        self._open_logs_btn.setText(
            self._text("training.action.open_logs")
        )
        self._create_run_btn.setText(
            self._text("training.action.create_run")
        )
        self._check_model_btn.setText(
            self._text("training.action.check_model")
        )
        self._test_inference_btn.setText(
            self._text("training.action.test_inference")
        )
        self._overview_card.set_title(
            self._text("training.card.overview.title")
        )
        self._overview_card.set_subtitle(
            self._text("training.card.overview.description")
        )
        self._checkpoints_card.set_title(
            self._text("training.card.checkpoints.title")
        )
        self._checkpoints_card.set_subtitle(
            self._text("training.card.checkpoints.description")
        )
        self._logs_card.set_title(
            self._text("training.card.logs.title")
        )
        self._logs_card.set_subtitle(
            self._text("training.card.logs.description")
        )
        self._create_run_card.set_title(
            self._text("training.card.create.title")
        )
        self._create_run_card.set_subtitle(
            self._text("training.card.create.description")
        )
        self._local_model_card.set_title(
            self._text("training.card.local_model.title")
        )
        self._local_model_card.set_subtitle(
            self._text("training.card.local_model.description")
        )
        for label, key in self._create_field_labels:
            label.setText(self._text(key))
        self._model_label.setText(self._text("training.field.model"))
        self._path_label.setText(self._text("training.field.path"))
        self._run_name.setPlaceholderText(
            self._text("training.placeholder.run_name")
        )
        self._inference_prompt.setPlaceholderText(
            self._text("training.placeholder.inference")
        )

    def _refresh_language(self, _locale: str = "") -> None:
        self._apply_static_text()
        self._populate_training_inputs()
        self._refresh_training_overview()
        self._refresh_local_model_block()

    def _refresh_stat_cards(self) -> None:
        self._clear_layout(self._stat_grid)
        for index, metric in enumerate(self._vm.stat_cards):
            card = QFrame()
            card.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(8)
            title = QLabel(
                self._render(self._vm.metric_title_model(metric))
            )
            title.setObjectName("CardTitle")
            value = QLabel(metric.value)
            value.setObjectName("MetricValue")
            note = make_muted_label(
                self._render(self._vm.metric_note_model(metric))
            )
            layout.addWidget(title)
            layout.addWidget(value)
            layout.addWidget(note)
            self._stat_grid.addWidget(card, index // 2, index % 2)

    def _refresh_checkpoints(self) -> None:
        self._clear_layout(self._checkpoint_layout)
        has_rows = False
        for checkpoint in self._vm.checkpoints:
            row = QFrame()
            row.setObjectName(
                "AccentCard" if checkpoint.highlighted else "PanelCardSoft"
            )
            layout = QVBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(4)
            title = QLabel(
                self._render(self._vm.checkpoint_name_model(checkpoint))
            )
            title.setObjectName("CardTitle")
            layout.addWidget(title)
            layout.addWidget(
                make_muted_label(
                    self._render(
                        self._vm.checkpoint_note_model(checkpoint)
                    )
                )
            )
            self._checkpoint_layout.addWidget(row)
            has_rows = True

        for version in self._vm.personality_versions:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(6)
            title_row = QHBoxLayout()
            title = QLabel(
                self._render(self._vm.version_title_model(version))
            )
            title.setObjectName("CardTitle")
            title_row.addWidget(title)
            title_row.addStretch(1)
            title_row.addWidget(
                make_status_label(
                    self._render(self._vm.version_status_model(version))
                )
            )
            layout.addLayout(title_row)
            layout.addWidget(
                make_muted_label(
                    self._render(self._vm.version_note_model(version))
                )
            )
            self._checkpoint_layout.addWidget(row)
            has_rows = True

        if not has_rows:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(4)
            layout.addWidget(
                QLabel(self._text("training.checkpoint.empty.title"))
            )
            layout.addWidget(
                make_muted_label(
                    self._text("training.checkpoint.empty.note")
                )
            )
            self._checkpoint_layout.addWidget(row)
        self._checkpoint_layout.addStretch(1)

    def _render_logs(self) -> tuple[str, ...]:
        return tuple(self._render(item) for item in self._vm.log_models())

    def _on_check_local_model(self) -> None:
        self._vm.check_local_model()
        self._refresh_local_model_block()

    def _on_test_inference(self) -> None:
        if self._thread_is_running(self._inference_thread):
            return
        ok, prompt = self._vm.begin_local_inference(
            self._inference_prompt.text()
        )
        if not ok:
            return
        self._refresh_local_model_block()

        thread = QThread(self)
        worker = _InferenceWorker(self._vm, prompt)
        self._inference_thread = thread
        self._inference_worker = worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_inference_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(
            lambda thread=thread, worker=worker: self._clear_inference_worker(
                thread,
                worker,
            )
        )
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _clear_inference_worker(
        self,
        thread: QThread,
        worker: _InferenceWorker,
    ) -> None:
        if self._inference_thread is thread:
            self._inference_thread = None
        if self._inference_worker is worker:
            self._inference_worker = None

    def _on_inference_finished(self, status: str, response: str) -> None:
        self._vm.finish_local_inference(status, response)
        self._refresh_local_model_block()

    def _refresh_local_model_block(self) -> None:
        self._model_value.setText(self._vm.local_model_name)
        self._path_value.setText(self._vm.local_model_path)
        self._local_model_status.setText(
            self._render(self._vm.local_model_status_model())
        )
        self._local_model_note.setText(
            self._render(self._vm.local_model_note_model())
        )
        inference_status = self._vm.local_inference_status_model()
        self._local_inference_note.setText(
            self._render(inference_status)
            if inference_status is not None
            else ""
        )
        self._local_inference_output.setPlainText(
            self._vm.inference_response
        )
        self._test_inference_btn.setEnabled(
            not self._vm.inference_in_progress
        )

    def _populate_training_inputs(self) -> None:
        selected_profile_id = str(
            self._profile_combo.currentData() or ""
        )
        self._profile_combo.clear()
        for profile in self._vm.profile_choices:
            self._profile_combo.addItem(profile.title, profile.profile_id)
        if self._profile_combo.count() > 0:
            selected_index = self._profile_combo.findData(
                selected_profile_id
            )
            self._profile_combo.setCurrentIndex(
                selected_index if selected_index >= 0 else 0
            )

        selected_dataset_id = str(
            self._dataset_combo.currentData() or ""
        )
        self._dataset_combo.clear()
        for dataset in self._vm.dataset_choices:
            label = self._text(
                "training.dataset.option",
                title=dataset.title,
                status=self._render(
                    self._vm.dataset_status_model(dataset)
                ),
            )
            self._dataset_combo.addItem(label, dataset.dataset_id)
        if self._dataset_combo.count() > 0:
            selected_index = self._dataset_combo.findData(
                selected_dataset_id
            )
            self._dataset_combo.setCurrentIndex(
                selected_index if selected_index >= 0 else 0
            )

        if self._profile_combo.count() == 0:
            self._create_run_btn.setEnabled(False)
            self._create_message.setText(
                self._text("training.message.profile_required")
            )
        else:
            self._create_run_btn.setEnabled(True)
            message = self._vm.current_message()
            self._create_message.setText(
                self._render(message) if message is not None else ""
            )

    def _on_create_run(self) -> None:
        success, _message = self._vm.create_training_run(
            title=self._run_name.text(),
            profile_id=str(self._profile_combo.currentData() or ""),
            dataset_id=str(self._dataset_combo.currentData() or ""),
            base_model=self._model_name.text(),
            epochs=self._epochs.value(),
            batch_size=self._batch_size.value(),
            learning_rate=float(self._learning_rate.value()),
        )
        message = self._vm.current_message()
        self._create_message.setText(
            self._render(message) if message is not None else ""
        )
        if success:
            self._run_name.clear()
            self._populate_training_inputs()
            self._refresh_training_overview()

    def _refresh_training_overview(self) -> None:
        self._title.setText(
            self._render(self._vm.header_title_model())
        )
        self._subtitle.setText(
            self._render(self._vm.header_subtitle_model())
        )
        self._status_label.setText(
            self._render(self._vm.status_model())
        )
        logs = self._render_logs()
        self._log_box.setPlainText("\n".join(logs))
        if self._logs_dialog is not None and self._logs_dialog.isVisible():
            self._logs_dialog.set_logs(logs)
        is_running = self._vm.training_in_progress
        self._launch_btn.setEnabled(
            self._vm.can_start_run and not is_running
        )
        self._launch_btn.setText(
            self._text("training.action.running")
            if is_running
            else self._text("training.action.launch")
        )
        self._progress_bar.set_value(self._vm.progress_value)
        self._progress_chip.setText(
            self._render(self._vm.progress_model())
        )
        self._artifact_path.setText(self._vm.artifact_path)
        self._refresh_stat_cards()
        self._refresh_checkpoints()

    def _on_open_logs(self) -> None:
        self._vm.poll_current_run()
        self._refresh_training_overview()
        if self._logs_dialog is None:
            self._logs_dialog = _TrainingLogsDialog(
                self,
                self._localization,
            )
        self._logs_dialog.set_logs(self._render_logs())
        self._logs_dialog.show()
        self._logs_dialog.raise_()
        self._logs_dialog.activateWindow()

    def _on_start_training(self) -> None:
        if self._thread_is_running(self._training_thread):
            return
        if not self._vm.begin_training_run():
            key = (
                "training.message.already_running"
                if self._vm.training_in_progress
                else "training.message.not_ready"
            )
            self._create_message.setText(self._text(key))
            return
        self._refresh_training_overview()
        self._create_message.setText(
            self._text("training.message.starting")
        )
        self._runner_timer.start()
        thread = QThread(self)
        worker = _TrainingWorker(self._vm)
        self._training_thread = thread
        self._training_worker = worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_training_started)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(
            lambda thread=thread, worker=worker: self._clear_training_worker(
                thread,
                worker,
            )
        )
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _clear_training_worker(
        self,
        thread: QThread,
        worker: _TrainingWorker,
    ) -> None:
        if self._training_thread is thread:
            self._training_thread = None
        if self._training_worker is worker:
            self._training_worker = None

    def _on_training_started(self, success: bool, _code: str) -> None:
        current_message = self._vm.current_message()
        self._create_message.setText(
            self._render(current_message)
            if current_message is not None
            else ""
        )
        self._refresh_training_overview()
        if success:
            self._runner_timer.start()

    def _on_runner_tick(self) -> None:
        self._vm.poll_current_run()
        self._refresh_training_overview()
        if not self._vm.training_in_progress:
            self._runner_timer.stop()

    def shutdown_background_work(self, timeout_ms: int = 0) -> bool:
        self._runner_timer.stop()
        if self._logs_dialog is not None:
            self._logs_dialog.close()

        timeout_ms = max(0, int(timeout_ms))
        deadline = monotonic() + timeout_ms / 1000 if timeout_ms else 0.0
        all_stopped = True
        for thread in (self._inference_thread, self._training_thread):
            if not self._thread_is_running(thread):
                continue
            assert thread is not None
            thread.quit()
            if deadline:
                remaining_ms = max(0, int((deadline - monotonic()) * 1000))
                if remaining_ms:
                    thread.wait(remaining_ms)
            if self._thread_is_running(thread):
                all_stopped = False
        return all_stopped

    @staticmethod
    def _thread_is_running(thread: QThread | None) -> bool:
        if thread is None:
            return False
        try:
            return thread.isRunning()
        except RuntimeError:
            return False

    @staticmethod
    def _clear_layout(layout: QGridLayout | QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if not self.shutdown_background_work(2_000):
            event.ignore()
            return
        super().closeEvent(event)
