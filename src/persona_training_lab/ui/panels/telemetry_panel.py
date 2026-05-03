from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QStyle, QStyleOptionFrame, QVBoxLayout, QWidget

from persona_training_lab.ui.viewmodels.telemetry import TelemetryMetricView, TelemetryViewModel


@dataclass(slots=True, frozen=True)
class TelemetryItem:
    short_label: str
    full_label: str
    value: int
    tooltip: str
    value_text: str


class _TelemetryBarTrack(QFrame):
    def __init__(self, value: int, *, vertical: bool) -> None:
        super().__init__()
        self.setObjectName("TelemetryBarTrack")
        self._value = max(0, min(100, value))
        self._vertical = vertical
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._fill_probe = QFrame(self)
        self._fill_probe.setObjectName("TelemetryBarFill")
        self._fill_probe.hide()

    def set_value(self, value: int) -> None:
        self._value = max(0, min(100, value))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        opt = QStyleOptionFrame()
        opt.initFrom(self)
        opt.rect = self.rect()
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

        radius = min(10.0, rect.width() / 2.0, rect.height() / 2.0)
        track_path = QPainterPath()
        track_path.addRoundedRect(rect, radius, radius)
        painter.save()
        painter.setClipPath(track_path)

        fill_rect = type(rect)(rect)
        if self._vertical:
            fill_height = max(8, int(rect.height() * self._value / 100))
            fill_rect.setTop(fill_rect.bottom() - fill_height + 1)
        else:
            fill_width = max(8, int(rect.width() * self._value / 100))
            fill_rect.setRight(fill_rect.left() + fill_width - 1)

        fill_opt = QStyleOptionFrame()
        fill_opt.initFrom(self._fill_probe)
        fill_opt.rect = fill_rect
        self._fill_probe.style().drawPrimitive(QStyle.PE_Widget, fill_opt, painter, self._fill_probe)
        painter.restore()


class _VerticalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self.setProperty("transparentBg", True)
        self.setToolTip(item.tooltip)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        track = _TelemetryBarTrack(item.value, vertical=True)
        track.setFixedSize(28, 86)

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
        self._track = track
        self._value_label = value_label

    def set_item(self, item: TelemetryItem) -> None:
        self.setToolTip(item.tooltip)
        self._track.set_value(item.value)
        self._value_label.setText(item.value_text)


class _HorizontalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self.setProperty("transparentBg", True)
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

        track = _TelemetryBarTrack(item.value, vertical=False)
        track.setMinimumHeight(28)
        track.setMaximumHeight(28)
        track.setFixedWidth(184)

        layout.addWidget(track)
        value_label = QLabel(item.value_text)
        value_label.setObjectName("TelemetryCaption")
        layout.addWidget(value_label)
        layout.addStretch(1)
        self._track = track
        self._value_label = value_label

    def set_item(self, item: TelemetryItem) -> None:
        self.setToolTip(item.tooltip)
        self._track.set_value(item.value)
        self._value_label.setText(item.value_text)


class TelemetryPanel(QFrame):
    def __init__(self, view_model: TelemetryViewModel) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._vm = view_model
        self._items = self._to_items(self._vm.metric_items())
        self._mode: str | None = None
        self._refresh_pending = False
        self._metrics_widgets: list[_VerticalMetric | _HorizontalMetric] = []
        self._metrics_layout: QVBoxLayout | QHBoxLayout | None = None
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(30_000)
        self._auto_refresh_timer.timeout.connect(self._on_auto_refresh)

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
        self._auto_refresh_timer.start()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        desired = "side" if self.width() < max(460, self.height() * 0.72) else "bottom"
        if desired != self._mode:
            self._rebuild(desired)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if not self._auto_refresh_timer.isActive():
            self._auto_refresh_timer.start()
        self._on_auto_refresh()

    def hideEvent(self, event) -> None:  # type: ignore[override]
        super().hideEvent(event)
        self._auto_refresh_timer.stop()

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
        self._run_refresh(show_pending=True)

    def _on_auto_refresh(self) -> None:
        self._run_refresh(show_pending=False)

    def _run_refresh(self, *, show_pending: bool) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True
        if show_pending:
            self._refresh_btn.setEnabled(False)
            self._refresh_btn.setText("Обновление...")
        QTimer.singleShot(0, self._finish_refresh)

    def _finish_refresh(self) -> None:
        try:
            self._vm.refresh()
            self._title.setText(self._vm.status_title)
            self._subtitle.setText(self._compact_updated_text(self._vm.status_subtitle))
            self._error.setText(self._vm.status_error)
            self._items = self._to_items(self._vm.metric_items())
            self._refresh_processes()
            self._update_metric_widgets()
        finally:
            self._refresh_btn.setText("Обновить")
            self._refresh_btn.setEnabled(True)
            self._refresh_pending = False

    def _compact_updated_text(self, subtitle: str) -> str:
        prefix = "Последнее обновление:"
        if subtitle.startswith(prefix):
            return f"Обновлено:{subtitle[len(prefix):]}"
        return subtitle

    def _update_metric_widgets(self) -> None:
        if len(self._metrics_widgets) != len(self._items):
            self._rebuild(self._mode or "bottom")
            return
        for widget, item in zip(self._metrics_widgets, self._items):
            widget.set_item(item)

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
            self._metrics_layout = layout
            self._metrics_widgets = []
            for item in self._items:
                metric = _HorizontalMetric(item)
                self._metrics_widgets.append(metric)
                layout.addWidget(metric)
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
            self._metrics_layout = layout
            self._metrics_widgets = []
            for item in self._items:
                metric = _VerticalMetric(item)
                self._metrics_widgets.append(metric)
                layout.addWidget(metric)
            outer.addWidget(row, 0, Qt.AlignLeft | Qt.AlignTop)
