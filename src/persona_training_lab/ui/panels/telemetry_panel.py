from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

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
        track.setAttribute(Qt.WA_StyledBackground, True)

        fill = QFrame(track)
        fill.setObjectName("TelemetryBarFill")
        fill.setAttribute(Qt.WA_StyledBackground, True)
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
        track.setAttribute(Qt.WA_StyledBackground, True)

        fill = QFrame(track)
        fill.setObjectName("TelemetryBarFill")
        fill.setAttribute(Qt.WA_StyledBackground, True)
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
        self._refresh_pending = False

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 14, 14, 14)
        self._root.setSpacing(10)

        title_row = QHBoxLayout()
        self._title = QLabel(self._vm.status_title)
        title_row.addWidget(self._title)
        title_row.addStretch(1)
        self._refresh_btn = QPushButton("Обновить")
        self._refresh_btn.setObjectName("SecondaryButton")
        self._refresh_btn.clicked.connect(self._on_refresh)
        title_row.addWidget(self._refresh_btn)
        self._root.addLayout(title_row)

        self._subtitle = QLabel(self._vm.status_subtitle)
        self._subtitle.setObjectName("MutedText")
        self._root.addWidget(self._subtitle)

        self._error = QLabel(self._vm.status_error)
        self._error.setObjectName("MutedText")
        self._root.addWidget(self._error)

        body_row = QHBoxLayout()
        body_row.setSpacing(12)
        self._root.addLayout(body_row, 1)

        self._content = QWidget()
        self._content.setObjectName("TelemetryMetricsHost")
        self._content.setProperty("transparentBg", True)
        body_row.addWidget(self._content, 2)

        processes_shell = QFrame()
        processes_shell.setObjectName("PanelCardSoft")
        processes_shell.setMaximumWidth(420)
        processes_shell.setMinimumWidth(280)
        processes_shell_layout = QVBoxLayout(processes_shell)
        processes_shell_layout.setContentsMargins(10, 10, 10, 10)
        processes_shell_layout.setSpacing(8)

        header = QLabel("Процессы")
        header.setObjectName("TelemetryChip")
        processes_shell_layout.addWidget(header)

        self._processes_scroll = QScrollArea()
        self._processes_scroll.setObjectName("TelemetryProcessesScroll")
        self._processes_scroll.setWidgetResizable(True)
        self._processes_scroll.setFrameShape(QFrame.NoFrame)
        self._processes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._processes_scroll.setMaximumHeight(138)
        self._processes_scroll.viewport().setObjectName("TelemetryProcessesViewport")

        self._processes_container = QWidget()
        self._processes_container.setObjectName("TelemetryProcessesContainer")
        self._processes_container.setProperty("transparentBg", True)
        self._processes = QVBoxLayout(self._processes_container)
        self._processes.setContentsMargins(0, 0, 0, 0)
        self._processes.setSpacing(6)
        self._processes_scroll.setWidget(self._processes_container)
        processes_shell_layout.addWidget(self._processes_scroll, 1)
        body_row.addWidget(processes_shell, 1)

        self._refresh_processes()
        self._rebuild("bottom")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        desired = "side" if self.width() < max(460, self.height() * 0.72) else "bottom"
        if desired != self._mode:
            self._rebuild(desired)

    def _to_items(self, metrics: tuple[TelemetryMetricView, ...]) -> list[TelemetryItem]:
        cpu_tooltip = self._vm.cpu_cores_text.strip()
        return [
            TelemetryItem(
                short_label=item.short_label,
                full_label=item.full_label,
                value=max(0, min(100, item.value_percent)),
                tooltip=f"{item.tooltip}\n{cpu_tooltip}" if item.short_label == "CPU" and cpu_tooltip else item.tooltip,
                value_text=item.value_text,
            )
            for item in metrics
        ]

    def _on_refresh(self) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("Обновление...")
        QTimer.singleShot(0, self._finish_refresh)

    def _finish_refresh(self) -> None:
        try:
            self._vm.refresh()
            self._title.setText(self._vm.status_title)
            self._subtitle.setText(self._vm.status_subtitle)
            self._error.setText(self._vm.status_error)
            self._items = self._to_items(self._vm.metric_items())
            self._refresh_processes()
            self._rebuild(self._mode or "bottom")
        finally:
            self._refresh_btn.setText("Обновить")
            self._refresh_btn.setEnabled(True)
            self._refresh_pending = False

    def _refresh_processes(self) -> None:
        while self._processes.count():
            item = self._processes.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

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
            center.setObjectName("TelemetryMetricsViewport")
            center.setProperty("transparentBg", True)
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
            row.setObjectName("TelemetryMetricsViewport")
            row.setProperty("transparentBg", True)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
            for item in self._items:
                layout.addWidget(_VerticalMetric(item))
            outer.addWidget(row, 0, Qt.AlignLeft | Qt.AlignTop)
