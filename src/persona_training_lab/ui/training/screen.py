from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
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
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


class TrainingScreen(QWidget):
    def __init__(self, view_model: TrainingViewModel) -> None:
        super().__init__()
        self._vm = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)
        self._title = QLabel(self._vm.title)
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label(self._vm.subtitle)
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        root.addWidget(header)

        actions = QFrame()
        actions.setObjectName("PanelCardSoft")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(18, 16, 18, 16)
        actions_layout.setSpacing(12)
        self._status_label = make_status_label(self._vm.status)
        actions_layout.addWidget(self._status_label)
        for text in ["Пауза", "Остановить", "Открыть логи"]:
            btn = QPushButton(text)
            btn.setObjectName("SecondaryButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(34)
            actions_layout.addWidget(btn)
        self._launch_btn = QPushButton("Запустить обучение")
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

        overview = PanelCard("Сеанс обучения", "Сердце процесса: прогресс, стабильность и checkpoints.")
        stat_grid = QGridLayout()
        stat_grid.setSpacing(12)
        for idx, metric in enumerate(self._vm.stat_cards):
            card = QFrame()
            card.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(8)
            t = QLabel(metric.title)
            t.setObjectName("CardTitle")
            v = QLabel(metric.value)
            v.setObjectName("MetricValue")
            n = make_muted_label(metric.note)
            layout.addWidget(t)
            layout.addWidget(v)
            layout.addWidget(n)
            stat_grid.addWidget(card, idx // 2, idx % 2)
        overview._layout.addLayout(stat_grid)
        progress = RoundedMetricBar(61, height=14)
        progress_wrap = QVBoxLayout()
        progress_wrap.setSpacing(8)
        progress_wrap.addWidget(progress)
        progress_chip = QLabel("Прогресс обучения · 61% | шаг 18 420 из целевого диапазона")
        progress_chip.setObjectName("TelemetryChip")
        progress_wrap.addWidget(progress_chip, 0, Qt.AlignLeft)
        overview._layout.addLayout(progress_wrap)
        left.addWidget(overview)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        left.addLayout(lower, 1)

        checkpoints_card = PanelCard("Чекпоинты и версии личности", "Единая лента артефактов обучения.")

        cp_scroll = QScrollArea()
        cp_scroll.setObjectName("StableScrollArea")
        cp_scroll.setWidgetResizable(True)
        cp_scroll.setFrameShape(QFrame.NoFrame)
        cp_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cp_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cp_scroll.setMinimumHeight(250)
        apply_scrollbar_style(cp_scroll)

        # внешний большой закруглённый контейнер
        cp_outer = QFrame()
        cp_outer.setObjectName("CheckpointScrollShell")

        cp_outer_layout = QVBoxLayout(cp_outer)
        cp_outer_layout.setContentsMargins(14, 14, 14, 14)
        cp_outer_layout.setSpacing(0)

        # внутренний прозрачный слой
        cp_wrap = QWidget()
        cp_wrap.setObjectName("CheckpointScrollWrap")
        cp_wrap.setStyleSheet("""
        QWidget#CheckpointScrollWrap {
            background: transparent;
            border: none;
        }
        """)

        cp_layout = QVBoxLayout(cp_wrap)
        cp_layout.setContentsMargins(0, 0, 0, 0)
        cp_layout.setSpacing(10)

        has_checkpoint_rows = False
        for item in self._vm.checkpoints:
            row = QFrame()
            row.setObjectName("AccentCard" if item.highlighted else "PanelCardSoft")

            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(4)

            lbl = QLabel(item.name)
            lbl.setObjectName("CardTitle")
            rl.addWidget(lbl)
            rl.addWidget(make_muted_label(item.note))

            cp_layout.addWidget(row)
            has_checkpoint_rows = True

        for version in self._vm.personality_versions:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(6)
            title_row = QHBoxLayout()
            title = QLabel(f"Версия личности · {version.title}")
            title.setObjectName("CardTitle")
            title_row.addWidget(title)
            title_row.addStretch(1)
            title_row.addWidget(make_status_label(version.status))
            rl.addLayout(title_row)
            rl.addWidget(make_muted_label(version.note))
            cp_layout.addWidget(row)
            has_checkpoint_rows = True

        if not has_checkpoint_rows:
            empty_row = QFrame()
            empty_row.setObjectName("PanelCardSoft")
            empty_layout = QVBoxLayout(empty_row)
            empty_layout.setContentsMargins(12, 10, 12, 10)
            empty_layout.setSpacing(4)
            empty_layout.addWidget(QLabel("Чекпоинты и версии личности"))
            empty_layout.addWidget(make_muted_label("Чекпоинты и версии личности пока не созданы"))
            cp_layout.addWidget(empty_row)

        cp_layout.addStretch(1)
        cp_outer_layout.addWidget(cp_wrap)
        cp_scroll.setWidget(cp_outer)

        checkpoints_card.add_widget(cp_scroll)
        lower.addWidget(checkpoints_card, 1)

        logs_card = PanelCard("Живые логи", "Технический хвост рядом, но не ломает основной фокус.")
        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setPlainText("\n".join(self._vm.logs))
        is_running = self._vm.status == "Выполняется"
        self._launch_btn.setEnabled(self._vm.can_start_run and not is_running)
        self._launch_btn.setText("Выполняется…" if is_running else "Запустить обучение")
        logs_card.add_widget(self._log_box)
        lower.addWidget(logs_card, 1)

        right = QVBoxLayout()
        right.setSpacing(16)
        body.addLayout(right, 2)

        create_run = PanelCard("Новый запуск обучения", "Подготовка run без реального старта обучения.")
        create_layout = QGridLayout()
        create_layout.setHorizontalSpacing(8)
        create_layout.setVerticalSpacing(8)

        self._run_name = QLineEdit()
        self._run_name.setPlaceholderText("Название запуска")
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

        create_layout.addWidget(make_muted_label("Название запуска"), 0, 0)
        create_layout.addWidget(self._run_name, 0, 1)
        create_layout.addWidget(make_muted_label("Профиль"), 1, 0)
        create_layout.addWidget(self._profile_combo, 1, 1)
        create_layout.addWidget(make_muted_label("Датасет"), 2, 0)
        create_layout.addWidget(self._dataset_combo, 2, 1)
        create_layout.addWidget(make_muted_label("Модель"), 3, 0)
        create_layout.addWidget(self._model_name, 3, 1)
        create_layout.addWidget(make_muted_label("Эпохи"), 4, 0)
        create_layout.addWidget(self._epochs, 4, 1)
        create_layout.addWidget(make_muted_label("Batch size"), 5, 0)
        create_layout.addWidget(self._batch_size, 5, 1)
        create_layout.addWidget(make_muted_label("Learning rate"), 6, 0)
        create_layout.addWidget(self._learning_rate, 6, 1)

        self._create_run_btn = QPushButton("Создать запуск")
        self._create_run_btn.setObjectName("SecondaryButton")
        self._create_run_btn.clicked.connect(self._on_create_run)
        create_layout.addWidget(self._create_run_btn, 7, 0, 1, 2)

        self._create_message = make_muted_label(self._vm.creation_message)
        create_layout.addWidget(self._create_message, 8, 0, 1, 2)
        self._populate_training_inputs()
        create_run._layout.addLayout(create_layout)
        right.addWidget(create_run)

        local_model = PanelCard("Локальная модель", "Проверка наличия локальной модели без загрузки в память.")
        local_rows = QVBoxLayout()
        local_rows.setSpacing(10)

        model_row = QFrame()
        model_row.setObjectName("PanelCardSoft")
        model_layout = QHBoxLayout(model_row)
        model_layout.setContentsMargins(12, 10, 12, 10)
        model_layout.setSpacing(10)
        model_layout.addWidget(make_muted_label("Модель"))
        model_layout.addStretch(1)
        model_layout.addWidget(QLabel(self._vm.local_model_name), 0, Qt.AlignRight)
        local_rows.addWidget(model_row)

        path_row = QFrame()
        path_row.setObjectName("PanelCardSoft")
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(12, 10, 12, 10)
        path_layout.setSpacing(10)
        path_layout.addWidget(make_muted_label("Путь"))
        path_layout.addStretch(1)
        path_layout.addWidget(QLabel(self._vm.local_model_path), 0, Qt.AlignRight)
        local_rows.addWidget(path_row)

        self._local_model_status = make_status_label(self._vm.local_model_status)
        local_rows.addWidget(self._local_model_status)

        self._local_model_note = make_muted_label(self._vm.local_model_note)
        local_rows.addWidget(self._local_model_note)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self._check_model_btn = QPushButton("Проверить модель")
        self._check_model_btn.setObjectName("SecondaryButton")
        self._check_model_btn.clicked.connect(self._on_check_local_model)
        controls.addWidget(self._check_model_btn)

        self._test_inference_btn = QPushButton("Проверить ответ")
        self._test_inference_btn.setObjectName("SecondaryButton")
        self._test_inference_btn.clicked.connect(self._on_test_inference)
        controls.addWidget(self._test_inference_btn)
        controls.addStretch(1)
        local_rows.addLayout(controls)

        self._inference_prompt = QLineEdit(self._vm.inference_prompt)
        self._inference_prompt.setPlaceholderText("MIA_SENTINEL_FT_TEST_001")
        local_rows.addWidget(self._inference_prompt)

        self._local_inference_note = make_muted_label(self._vm.local_inference_status)
        local_rows.addWidget(self._local_inference_note)
        self._local_inference_output = QTextEdit()
        self._local_inference_output.setReadOnly(True)
        self._local_inference_output.setMaximumHeight(84)
        self._local_inference_output.setPlainText(self._vm.inference_response)
        local_rows.addWidget(self._local_inference_output)

        local_model._layout.addLayout(local_rows)
        right.addWidget(local_model)

        right.addStretch(1)

        self._runner_timer = QTimer(self)
        self._runner_timer.setInterval(600)
        self._runner_timer.timeout.connect(self._on_runner_tick)
        self._refresh_training_overview()

    def _on_check_local_model(self) -> None:
        self._vm.check_local_model()
        self._refresh_local_model_block()

    def _on_test_inference(self) -> None:
        self._test_inference_btn.setEnabled(False)
        self._vm.test_local_inference(self._inference_prompt.text())
        self._refresh_local_model_block()
        self._test_inference_btn.setEnabled(True)

    def _refresh_local_model_block(self) -> None:
        self._local_model_status.setText(self._vm.local_model_status)
        self._local_model_note.setText(self._vm.local_model_note)
        self._local_inference_note.setText(self._vm.local_inference_status)
        self._local_inference_output.setPlainText(self._vm.inference_response)

    def _populate_training_inputs(self) -> None:
        selected_profile_id = str(self._profile_combo.currentData() or "")
        self._profile_combo.clear()
        for profile in self._vm.profile_choices:
            self._profile_combo.addItem(profile.title, profile.profile_id)
        if self._profile_combo.count() > 0:
            selected_index = self._profile_combo.findData(selected_profile_id)
            self._profile_combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)

        selected_dataset_id = str(self._dataset_combo.currentData() or "")
        self._dataset_combo.clear()
        for dataset in self._vm.dataset_choices:
            label = f"{dataset.title} ({dataset.status})"
            self._dataset_combo.addItem(label, dataset.dataset_id)
        if self._dataset_combo.count() > 0:
            selected_dataset_index = self._dataset_combo.findData(selected_dataset_id)
            self._dataset_combo.setCurrentIndex(selected_dataset_index if selected_dataset_index >= 0 else 0)

        if self._profile_combo.count() == 0:
            self._create_run_btn.setEnabled(False)
            self._create_message.setText("Сначала создайте профиль личности")
        else:
            self._create_run_btn.setEnabled(True)
            self._create_message.setText(self._vm.creation_message)

    def _on_create_run(self) -> None:
        success, message = self._vm.create_training_run(
            title=self._run_name.text(),
            profile_id=str(self._profile_combo.currentData() or ""),
            dataset_id=str(self._dataset_combo.currentData() or ""),
            base_model=self._model_name.text(),
            epochs=self._epochs.value(),
            batch_size=self._batch_size.value(),
            learning_rate=float(self._learning_rate.value()),
        )
        self._create_message.setText(message)
        if success:
            self._run_name.clear()
            self._populate_training_inputs()
            self._refresh_training_overview()

    def _refresh_training_overview(self) -> None:
        self._title.setText(self._vm.title)
        self._subtitle.setText(self._vm.subtitle)
        self._status_label.setText(self._vm.status)
        self._log_box.setPlainText("\n".join(self._vm.logs))
        is_running = self._vm.status == "Выполняется"
        self._launch_btn.setEnabled(self._vm.can_start_run and not is_running)
        self._launch_btn.setText("Выполняется…" if is_running else "Запустить обучение")


    def _on_start_training(self) -> None:
        success, message = self._vm.start_selected_training_run()
        self._create_message.setText(message)
        self._refresh_training_overview()
        if success:
            self._runner_timer.start()

    def _on_runner_tick(self) -> None:
        finished = self._vm.refresh_current_run()
        self._refresh_training_overview()
        if finished:
            self._runner_timer.stop()
