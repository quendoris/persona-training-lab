from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget

from persona_training_lab.ui.viewmodels.telemetry import TelemetryMetricView, TelemetryViewModel


@dataclass(slots=True, frozen=True)
class TelemetryItem:
    short_label: str
    full_label: str
    value: int
    tooltip: str
    value_text: str


class _VerticalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self._item = item
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._track = QFrame()
        self._track.setObjectName("TelemetryBarTrack")
        self._track.setFixedSize(28, 86)

        self._fill = QFrame(self._track)
        self._fill.setObjectName("TelemetryBarFill")

        layout.addWidget(self._track, 0, Qt.AlignHCenter)

        self._caption = QLabel()
        self._caption.setObjectName("TelemetryChip")
        self._caption.setAlignment(Qt.AlignCenter)
        self._caption.setMinimumWidth(42)
        self._caption.setFixedHeight(24)
        layout.addWidget(self._caption, 0, Qt.AlignHCenter)

        self._value_label = QLabel()
        self._value_label.setObjectName("TelemetryCaption")
        self._value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._value_label)

        self.update_item(item)

    def update_item(self, item: TelemetryItem) -> None:
        self._item = item
        self.setToolTip(item.tooltip)
        self._caption.setText(item.short_label)
        self._value_label.setText(item.value_text)
        height = max(8, int(86 * item.value / 100))
        self._fill.setGeometry(0, 86 - height, 28, height)
        self._fill.show()


class _HorizontalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self._item = item
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._label = QLabel()
        self._label.setObjectName("TelemetryChip")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumWidth(64)
        self._label.setFixedHeight(24)
        layout.addWidget(self._label)

        self._track = QFrame()
        self._track.setObjectName("TelemetryBarTrack")
        self._track.setMinimumHeight(28)
        self._track.setMaximumHeight(28)
        self._track.setFixedWidth(184)

        self._fill = QFrame(self._track)
        self._fill.setObjectName("TelemetryBarFill")
        layout.addWidget(self._track)

        self._value_label = QLabel()
        self._value_label.setObjectName("TelemetryCaption")
        layout.addWidget(self._value_label)
        layout.addStretch(1)

        self.update_item(item)

    def update_item(self, item: TelemetryItem) -> None:
        self._item = item
        self.setToolTip(item.tooltip)
        self._label.setText(item.full_label)
        self._value_label.setText(item.value_text)
        width = max(8, int(184 * item.value / 100))
        self._fill.setGeometry(0, 0, width, 28)
        self._fill.show()


class TelemetryPanel(QFrame):
    def __init__(self, view_model: TelemetryViewModel) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._vm = view_model
        self._mode: str | None = None
        self._metric_widgets: list[_VerticalMetric | _HorizontalMetric] = []

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(10, 10, 10, 10)
        self._root.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self._status = QLabel(self._vm.status_title)
        self._status.setObjectName("TelemetryChip")
        top_row.addWidget(self._status, 0, Qt.AlignLeft)

        self._time = QLabel(self._vm.status_subtitle)
        self._time.setObjectName("MutedText")
        top_row.addWidget(self._time, 0, Qt.AlignLeft)
        top_row.addStretch(1)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.setFocusPolicy(Qt.NoFocus)
        refresh_btn.clicked.connect(self._on_refresh)
        top_row.addWidget(refresh_btn)
        self._root.addLayout(top_row)

        self._error = QLabel(self._vm.status_error)
        self._error.setObjectName("MutedText")
        self._root.addWidget(self._error)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        self._root.addWidget(splitter, 1)

        self._left_shell = QFrame()
        self._left_shell.setProperty("transparentBg", True)
        self._left_shell.setMinimumWidth(280)
        left_shell_layout = QVBoxLayout(self._left_shell)
        left_shell_layout.setContentsMargins(2, 2, 2, 2)
        left_shell_layout.setSpacing(2)

        self._metrics_host = QWidget()
        self._metrics_host.setProperty("transparentBg", True)
        left_shell_layout.addWidget(self._metrics_host, 1)
        splitter.addWidget(self._left_shell)

        self._right_shell = QFrame()
        self._right_shell.setObjectName("PanelCardSoft")
        self._right_shell.setMinimumWidth(280)
        self._right_shell.setMaximumWidth(480)
        right_shell_layout = QVBoxLayout(self._right_shell)
        right_shell_layout.setContentsMargins(10, 8, 10, 8)
        right_shell_layout.setSpacing(6)

        self._processes_scroll = QScrollArea()
        self._processes_scroll.setWidgetResizable(True)
        self._processes_scroll.setFrameShape(QFrame.NoFrame)
        self._processes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._processes_scroll.setMaximumHeight(120)

        self._processes_container = QWidget()
        self._processes_layout = QVBoxLayout(self._processes_container)
        self._processes_layout.setContentsMargins(0, 0, 0, 0)
        self._processes_layout.setSpacing(4)
        self._processes_scroll.setWidget(self._processes_container)
        right_shell_layout.addWidget(self._processes_scroll, 1)
        splitter.addWidget(self._right_shell)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 520])

        self._refresh_processes()
        self._rebuild("bottom")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        desired = "side" if self.width() < max(650, self.height() * 0.9) else "bottom"
        if desired != self._mode:
            self._rebuild(desired)

    def _to_items(self, metrics: tuple[TelemetryMetricView, ...]) -> list[TelemetryItem]:
        result: list[TelemetryItem] = []
        for item in metrics:
            tooltip = item.tooltip
            if item.short_label == "CPU":
                tooltip = f"{item.tooltip} · {self._vm.cpu_cores_text}"
            result.append(
                TelemetryItem(
                    short_label=item.short_label,
                    full_label=item.full_label,
                    value=max(0, min(100, item.value_percent)),
                    tooltip=tooltip,
                    value_text=item.value_text,
                )
            )
        return result

    def _on_refresh(self) -> None:
        self._vm.refresh()
        self._status.setText(self._vm.status_title)
        now_text = QDateTime.currentDateTime().toString("HH:mm:ss.zzz")
        self._time.setText(f"Обновлено: {now_text}")
        self._error.setText(self._vm.status_error)
        self._refresh_processes()
        self._update_metric_widgets()

    def _refresh_processes(self) -> None:
        while self._processes_layout.count():
            item = self._processes_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for row in self._vm.processes_rows:
            label = QLabel(row)
            label.setObjectName("TelemetryCaption")
            self._processes_layout.addWidget(label)

    def _rebuild(self, mode: str) -> None:
        self._mode = mode
        old_layout = self._metrics_host.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            old_layout.deleteLater()

        self._metric_widgets.clear()
        items = self._to_items(self._vm.metric_items())

        if mode == "side":
            outer = QVBoxLayout(self._metrics_host)
            outer.setContentsMargins(0, 2, 0, 2)
            outer.setSpacing(6)
            for item in items:
                widget = _HorizontalMetric(item)
                self._metric_widgets.append(widget)
                outer.addWidget(widget)
            outer.addStretch(1)
        else:
            outer = QVBoxLayout(self._metrics_host)
            outer.setContentsMargins(0, 2, 0, 2)
            outer.setSpacing(4)
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            for item in items:
                widget = _VerticalMetric(item)
                self._metric_widgets.append(widget)
                layout.addWidget(widget)
            layout.addStretch(1)
            outer.addWidget(row, 0, Qt.AlignCenter)

    def _update_metric_widgets(self) -> None:
        items = self._to_items(self._vm.metric_items())
        if len(items) != len(self._metric_widgets):
            self._rebuild(self._mode or "bottom")
            return
        for widget, item in zip(self._metric_widgets, items, strict=True):
            widget.update_item(item)
