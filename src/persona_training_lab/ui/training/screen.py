from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWidget, QScrollArea, QPushButton

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.metrics import RoundedMetricBar
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
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
        title = QLabel(self._vm.title)
        title.setObjectName("ScreenTitle")
        subtitle = make_muted_label(self._vm.subtitle)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        actions = QFrame()
        actions.setObjectName("PanelCardSoft")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(18, 16, 18, 16)
        actions_layout.setSpacing(12)
        actions_layout.addWidget(make_status_label(self._vm.status))
        for text in ["Пауза", "Остановить", "Открыть логи"]:
            btn = QPushButton(text)
            btn.setObjectName("SecondaryButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(34)
            actions_layout.addWidget(btn)
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

        checkpoints_card = PanelCard("Лента чекпоинтов", "История run, а не просто список файлов.")

        cp_scroll = QScrollArea()
        cp_scroll.setWidgetResizable(True)
        cp_scroll.setFrameShape(QFrame.NoFrame)
        cp_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cp_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cp_scroll.setMinimumHeight(250)
        cp_scroll.setStyleSheet("""
        QScrollArea {
            background: transparent;
            border: none;
        }
        QScrollArea > QWidget > QWidget {
            background: transparent;
            border: none;
        }
        """)
        cp_scroll.viewport().setStyleSheet("background: transparent;")

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

        cp_layout.addStretch(1)
        cp_outer_layout.addWidget(cp_wrap)
        cp_scroll.setWidget(cp_outer)

        checkpoints_card.add_widget(cp_scroll)
        lower.addWidget(checkpoints_card, 1)

        logs_card = PanelCard("Живые логи", "Технический хвост рядом, но не ломает основной фокус.")
        log_box = QTextEdit()
        log_box.setReadOnly(True)
        log_box.setPlainText("\n".join(self._vm.logs))
        logs_card.add_widget(log_box)
        lower.addWidget(logs_card, 1)

        telemetry_bottom = PanelCard("Телеметрия нагрузки", "Нижние столбики ресурсов.")
        telemetry_rows = QVBoxLayout()
        telemetry_rows.setSpacing(10)
        for label, value, note in self._vm.monitor_rows:
            block = QFrame()
            block.setObjectName("PanelCardSoft")
            bl = QVBoxLayout(block)
            bl.setContentsMargins(12, 10, 12, 10)
            bl.setSpacing(6)
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(make_muted_label(note), 1, Qt.AlignRight)
            bl.addLayout(row)
            bl.addWidget(RoundedMetricBar(value=value, height=12))
            telemetry_rows.addWidget(block)
        telemetry_bottom._layout.addLayout(telemetry_rows)
        left.addWidget(telemetry_bottom, 0)

        right = QVBoxLayout()
        right.setSpacing(16)
        body.addLayout(right, 2)

        versions = PanelCard("Версии личности", "Артефакты обучения.")
        versions_rows = QVBoxLayout()
        versions_rows.setSpacing(10)

        if self._vm.versions_status_message:
            versions_rows.addWidget(make_muted_label(self._vm.versions_status_message))

        for version in self._vm.personality_versions:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(6)
            title_row = QHBoxLayout()
            title = QLabel(version.title)
            title.setObjectName("CardTitle")
            title_row.addWidget(title)
            title_row.addStretch(1)
            title_row.addWidget(make_status_label(version.status))
            rl.addLayout(title_row)
            rl.addWidget(make_muted_label(version.note))
            versions_rows.addWidget(row)

        versions._layout.addLayout(versions_rows)
        right.addWidget(versions)

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

        self._test_inference_btn = QPushButton("Тестовый ответ")
        self._test_inference_btn.setObjectName("SecondaryButton")
        self._test_inference_btn.clicked.connect(self._on_test_inference)
        controls.addWidget(self._test_inference_btn)
        controls.addStretch(1)
        local_rows.addLayout(controls)

        self._local_inference_note = make_muted_label(self._vm.local_inference_status)
        local_rows.addWidget(self._local_inference_note)

        local_model._layout.addLayout(local_rows)
        right.addWidget(local_model)

        risk = PanelCard(self._vm.risk_title, self._vm.risk_body)
        right.addWidget(risk)
        right.addStretch(1)

    def _on_check_local_model(self) -> None:
        self._vm.check_local_model()
        self._refresh_local_model_block()

    def _on_test_inference(self) -> None:
        self._vm.test_local_inference()
        self._refresh_local_model_block()

    def _refresh_local_model_block(self) -> None:
        self._local_model_status.setText(self._vm.local_model_status)
        self._local_model_note.setText(self._vm.local_model_note)
        self._local_inference_note.setText(self._vm.local_inference_status)
