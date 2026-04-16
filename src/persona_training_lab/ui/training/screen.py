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
        cp_scroll.setMinimumHeight(250)
        cp_wrap = QWidget()
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
        cp_scroll.setWidget(cp_wrap)
        checkpoints_card.add_widget(cp_scroll)
        lower.addWidget(checkpoints_card, 1)

        logs_card = PanelCard("Живые логи", "Технический хвост рядом, но не ломает основной фокус.")
        log_box = QTextEdit()
        log_box.setReadOnly(True)
        log_box.setPlainText("\n".join(self._vm.logs))
        logs_card.add_widget(log_box)
        lower.addWidget(logs_card, 1)

        right = QVBoxLayout()
        right.setSpacing(16)
        body.addLayout(right, 2)

        inspector = PanelCard("Контекст запуска", "Нельзя заставлять пользователя помнить, что именно выбрано.")
        rows = QVBoxLayout()
        rows.setSpacing(10)
        for key, value in self._vm.selected_objects:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(10)
            left_lbl = make_muted_label(key)
            right_lbl = QLabel(value)
            rl.addWidget(left_lbl, 1)
            rl.addWidget(right_lbl, 0, Qt.AlignRight)
            rows.addWidget(row)
        inspector._layout.addLayout(rows)
        right.addWidget(inspector)

        monitor = PanelCard("Мониторинг железа", "Цифры должны помогать, а не давить.")
        monitor_rows = QVBoxLayout()
        monitor_rows.setSpacing(12)
        for label, value, note in self._vm.monitor_rows:
            block = QFrame()
            block.setObjectName("PanelCardSoft")
            bl = QVBoxLayout(block)
            bl.setContentsMargins(12, 10, 12, 10)
            bl.setSpacing(8)
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(make_muted_label(note), 1, Qt.AlignRight)
            bl.addLayout(row)
            bl.addWidget(RoundedMetricBar(value=value, height=12))
            monitor_rows.addWidget(block)
        monitor._layout.addLayout(monitor_rows)
        right.addWidget(monitor)

        risk = PanelCard(self._vm.risk_title, self._vm.risk_body)
        right.addWidget(risk)

        next_card = PanelCard("Следующий лучший шаг", self._vm.next_step)
        right.addWidget(next_card)
        right.addStretch(1)
