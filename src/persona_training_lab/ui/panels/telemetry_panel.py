from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

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
        self.setToolTip(item.tooltip)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        track = QFrame()
        track.setObjectName("TelemetryBarTrack")
        track.setFixedSize(28, 86)

        fill = QFrame(track)
        fill.setObjectName("TelemetryBarFill")
        height = max(8, int(86 * item.value / 100))
        fill.setGeometry(0, 86 - height, 28, height)
        fill.show()

        layout.addWidget(track, 0, Qt.AlignHCenter)
        caption = QLabel(item.short_label)
        caption.setObjectName("TelemetryChip")
        caption.setAlignment(Qt.AlignCenter)
        caption.setMinimumWidth(42)
        caption.setFixedHeight(24)
        layout.addWidget(caption, 0, Qt.AlignHCenter)

        value_label = QLabel(item.value_text)
        value_label.setObjectName("TelemetryCaption")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)


class _HorizontalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self.setToolTip(item.tooltip)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QLabel(item.full_label)
        label.setObjectName("TelemetryChip")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumWidth(64)
        label.setFixedHeight(24)
        layout.addWidget(label)

        track = QFrame()
        track.setObjectName("TelemetryBarTrack")
        track.setMinimumHeight(28)
        track.setMaximumHeight(28)
        track.setFixedWidth(184)

        fill = QFrame(track)
        fill.setObjectName("TelemetryBarFill")
        width = max(8, int(184 * item.value / 100))
        fill.setGeometry(0, 0, width, 28)
        fill.show()

        layout.addWidget(track)
        value_label = QLabel(item.value_text)
        value_label.setObjectName("TelemetryCaption")
        layout.addWidget(value_label)
        layout.addStretch(1)


class TelemetryPanel(QFrame):
    def __init__(self, view_model: TelemetryViewModel) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._vm = view_model
        self._items = self._to_items(self._vm.metric_items())
        self._mode: str | None = None

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 14, 14, 14)
        self._root.setSpacing(10)

        title_row = QHBoxLayout()
        self._title = QLabel(self._vm.status_title)
        title_row.addWidget(self._title)
        title_row.addStretch(1)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.clicked.connect(self._on_refresh)
        title_row.addWidget(refresh_btn)
        self._root.addLayout(title_row)

        self._subtitle = QLabel(self._vm.status_subtitle)
        self._subtitle.setObjectName("MutedText")
        self._root.addWidget(self._subtitle)

        self._error = QLabel(self._vm.status_error)
        self._error.setObjectName("MutedText")
        self._root.addWidget(self._error)

        self._cores = QLabel(self._vm.cpu_cores_text)
        self._cores.setObjectName("MutedText")
        self._root.addWidget(self._cores)

        self._content = QWidget()
        self._content.setProperty("transparentBg", True)
        self._root.addWidget(self._content, 1)

        self._processes = QVBoxLayout()
        self._processes.setSpacing(6)
        self._root.addLayout(self._processes)
        self._refresh_processes()
        self._rebuild("bottom")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        desired = "side" if self.width() < max(460, self.height() * 0.72) else "bottom"
        if desired != self._mode:
            self._rebuild(desired)

    def _to_items(self, metrics: tuple[TelemetryMetricView, ...]) -> list[TelemetryItem]:
        return [
            TelemetryItem(
                short_label=item.short_label,
                full_label=item.full_label,
                value=max(0, min(100, item.value_percent)),
                tooltip=item.tooltip,
                value_text=item.value_text,
            )
            for item in metrics
        ]

    def _on_refresh(self) -> None:
        self._vm.refresh()
        self._title.setText(self._vm.status_title)
        self._subtitle.setText(self._vm.status_subtitle)
        self._error.setText(self._vm.status_error)
        self._cores.setText(self._vm.cpu_cores_text)
        self._items = self._to_items(self._vm.metric_items())
        self._refresh_processes()
        self._rebuild(self._mode or "bottom")

    def _refresh_processes(self) -> None:
        while self._processes.count():
            item = self._processes.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        header = QLabel("Процессы")
        header.setObjectName("TelemetryChip")
        self._processes.addWidget(header)
        for row in self._vm.processes_rows:
            self._processes.addWidget(QLabel(row))

    def _rebuild(self, mode: str) -> None:
        self._mode = mode
        old_layout = self._content.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            old_layout.deleteLater()

        if mode == "side":
            outer = QVBoxLayout(self._content)
            outer.setContentsMargins(0, 4, 0, 0)
            outer.setSpacing(8)
            center = QWidget()
            layout = QVBoxLayout(center)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            for item in self._items:
                layout.addWidget(_HorizontalMetric(item))
            outer.addWidget(center, 0, Qt.AlignTop)
        else:
            outer = QVBoxLayout(self._content)
            outer.setContentsMargins(0, 4, 0, 0)
            outer.setSpacing(8)
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
            for item in self._items:
                layout.addWidget(_VerticalMetric(item))
            outer.addWidget(row, 0, Qt.AlignLeft | Qt.AlignTop)
