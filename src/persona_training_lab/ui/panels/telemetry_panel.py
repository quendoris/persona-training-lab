from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QPainter, QPaintEvent, QPalette
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.viewmodels.telemetry import TelemetryMetricView, TelemetryViewModel


@dataclass(slots=True, frozen=True)
class TelemetryItem:
    short_label: str
    full_label: str
    value: int
    tooltip: str
    value_text: str


class _BarTrack(QWidget):
    def __init__(self, *, vertical: bool, length: int, thickness: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TelemetryBarTrack")
        self._vertical = vertical
        self._progress = 0
        if vertical:
            self.setFixedSize(thickness, length)
            self.setMinimumSize(thickness, length)
        else:
            self.setFixedSize(length, thickness)
            self.setMinimumSize(length, thickness)

    def set_progress(self, value: int) -> None:
        clamped = max(0, min(100, value))
        if clamped == self._progress:
            return
        self._progress = clamped
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = min(rect.width(), rect.height()) / 2.0
        palette = self.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        base_track = palette.color(QPalette.ColorRole.Midlight)
        base_fill = palette.color(QPalette.ColorRole.Highlight)
        if not base_fill.isValid() or base_fill.alpha() < 120:
            base_fill = palette.color(QPalette.ColorRole.Link)
        if not base_fill.isValid():
            base_fill = palette.color(QPalette.ColorRole.BrightText)

        contrast = abs(base_fill.lightness() - window_color.lightness())
        if contrast < 36:
            base_fill = base_fill.lighter(145) if window_color.lightness() < 128 else base_fill.darker(150)
        base_fill.setAlpha(max(190, base_fill.alpha()))

        track_color = base_track if base_track.isValid() else window_color
        track_contrast = abs(track_color.lightness() - window_color.lightness())
        if track_contrast < 16:
            track_color = window_color.lighter(125) if window_color.lightness() < 128 else window_color.darker(125)
        track_color.setAlpha(108)
        fill_color = base_fill
        painter.setPen(Qt.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect, radius, radius)

        if self._progress <= 0:
            return

        if self._vertical:
            fill_height = max(2, int(rect.height() * self._progress / 100))
            fill_rect = rect.adjusted(0, rect.height() - fill_height, 0, 0)
        else:
            fill_width = max(2, int(rect.width() * self._progress / 100))
            fill_rect = rect.adjusted(0, 0, -(rect.width() - fill_width), 0)

        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, radius, radius)


class _VerticalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self.setObjectName("TelemetryMetricItem")
        self.setProperty("transparentBg", True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(56, 148)
        self._item = item
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._track = _BarTrack(vertical=True, length=86, thickness=28)
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
        self._track.set_progress(item.value)


class _HorizontalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self.setObjectName("TelemetryMetricItem")
        self.setProperty("transparentBg", True)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(38)
        self._item = item
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._label = QLabel()
        self._label.setObjectName("TelemetryChip")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumWidth(62)
        self._label.setFixedHeight(24)
        layout.addWidget(self._label)

        self._track = _BarTrack(vertical=False, length=176, thickness=24)
        layout.addWidget(self._track)

        self._value_label = QLabel()
        self._value_label.setObjectName("TelemetryCaption")
        self._value_label.setMinimumWidth(86)
        layout.addWidget(self._value_label)
        layout.addStretch(1)

        self.update_item(item)

    def update_item(self, item: TelemetryItem) -> None:
        self._item = item
        self.setToolTip(item.tooltip)
        self._label.setText(item.full_label)
        self._value_label.setText(item.value_text)
        self._track.set_progress(item.value)


class TelemetryPanel(QFrame):
    def __init__(self, view_model: TelemetryViewModel) -> None:
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setAutoFillBackground(False)
        self.setProperty("transparentBg", True)
        self._vm = view_model
        self._mode: str | None = None
        self._metric_widgets: list[_VerticalMetric | _HorizontalMetric] = []
        self._dock_ref: QDockWidget | None = None

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(10, 8, 10, 8)
        self._root.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._time = QLabel(self._vm.status_subtitle)
        self._time.setObjectName("MutedText")
        top_row.addWidget(self._time, 0, Qt.AlignLeft)
        top_row.addStretch(1)

        self._error = QLabel(self._vm.status_error)
        self._error.setObjectName("MutedText")
        self._error.setVisible(bool(self._vm.status_error))
        top_row.addWidget(self._error, 0, Qt.AlignRight)

        self._refresh_btn = QPushButton("Обновить")
        self._refresh_btn.setObjectName("SecondaryButton")
        self._refresh_btn.setFocusPolicy(Qt.NoFocus)
        self._refresh_btn.clicked.connect(self._on_refresh)
        top_row.addWidget(self._refresh_btn)
        self._root.addLayout(top_row)

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setAutoFillBackground(False)
        self._splitter.setProperty("transparentBg", True)
        self._splitter.setStyleSheet("QSplitter, QSplitter::handle { background: transparent; border: none; }")
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(6)
        self._root.addWidget(self._splitter, 1)

        self._left_shell = QFrame()
        self._left_shell.setFrameShape(QFrame.NoFrame)
        self._left_shell.setAutoFillBackground(False)
        self._left_shell.setProperty("transparentBg", True)
        self._left_shell.setMinimumWidth(230)
        left_shell_layout = QVBoxLayout(self._left_shell)
        left_shell_layout.setContentsMargins(10, 6, 8, 6)
        left_shell_layout.setSpacing(2)

        self._metrics_host = QWidget()
        self._metrics_host.setObjectName("TelemetryMetricsHost")
        self._metrics_host.setAutoFillBackground(False)
        self._metrics_host.setProperty("transparentBg", True)
        self._metrics_host.setMinimumHeight(170)
        self._metrics_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_shell_layout.addWidget(self._metrics_host, 1)
        self._splitter.addWidget(self._left_shell)

        self._right_shell = QFrame()
        self._right_shell.setFrameShape(QFrame.NoFrame)
        self._right_shell.setAutoFillBackground(False)
        self._right_shell.setProperty("transparentBg", True)
        self._right_shell.setMinimumWidth(270)
        self._right_shell.setMaximumWidth(660)
        right_shell_layout = QVBoxLayout(self._right_shell)
        right_shell_layout.setContentsMargins(8, 4, 8, 4)
        right_shell_layout.setSpacing(0)

        self._processes_card = QFrame()
        self._processes_card.setObjectName("PanelCardSoft")
        processes_card_layout = QVBoxLayout(self._processes_card)
        processes_card_layout.setContentsMargins(10, 8, 10, 8)
        processes_card_layout.setSpacing(0)

        self._processes_scroll = QScrollArea()
        self._processes_scroll.setWidgetResizable(True)
        self._processes_scroll.setFrameShape(QFrame.NoFrame)
        self._processes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._processes_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._processes_scroll.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._processes_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._processes_scroll.setMinimumHeight(96)
        self._processes_scroll.setMaximumHeight(136)

        self._processes_container = QWidget()
        self._processes_layout = QVBoxLayout(self._processes_container)
        self._processes_layout.setContentsMargins(0, 0, 0, 0)
        self._processes_layout.setSpacing(4)
        self._processes_layout.setAlignment(Qt.AlignTop)
        self._processes_scroll.setWidget(self._processes_container)
        self._processes_container.setProperty("transparentBg", True)
        self._processes_scroll.viewport().setStyleSheet("background: transparent;")
        processes_card_layout.addWidget(self._processes_scroll, 1)
        right_shell_layout.addWidget(self._processes_card, 0, Qt.AlignTop)
        right_shell_layout.addStretch(1)
        self._splitter.addWidget(self._right_shell)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([470, 590])

        self._bind_dock_state()
        self._apply_size_policy()
        self._refresh_processes()
        self._rebuild("bottom")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        desired = "side" if self.width() < 520 else "bottom"
        if desired != self._mode:
            self._rebuild(desired)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._bind_dock_state()
        self._apply_size_policy()

    def _bind_dock_state(self) -> None:
        dock = self._find_dock_widget()
        if dock is None or dock is self._dock_ref:
            return
        self._dock_ref = dock
        dock.topLevelChanged.connect(lambda _floating: self._apply_size_policy())

    def _find_dock_widget(self) -> QDockWidget | None:
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QDockWidget):
                return parent
            parent = parent.parentWidget()
        return None

    def _apply_size_policy(self) -> None:
        is_floating = bool(self._dock_ref and self._dock_ref.isFloating())
        if is_floating:
            self._left_shell.setMinimumWidth(260)
            self._right_shell.setMinimumWidth(300)
            self.setMinimumWidth(740)
            self._splitter.setSizes([520, 620])
        else:
            self._left_shell.setMinimumWidth(160)
            self._right_shell.setMinimumWidth(260)
            self.setMinimumWidth(0)
            self._splitter.setSizes([470, 590])
        if self._mode is not None:
            self._rebuild(self._mode)

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
        self._refresh_btn.setEnabled(False)
        self._vm.refresh()
        now_text = QDateTime.currentDateTime().toString("HH:mm:ss")
        self._time.setText(f"Обновлено: {now_text}")
        self._error.setText(self._vm.status_error)
        self._error.setVisible(bool(self._vm.status_error))
        self._refresh_processes()
        self._update_metric_widgets()
        self._refresh_btn.setEnabled(True)

    def _refresh_processes(self) -> None:
        while self._processes_layout.count():
            item = self._processes_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for row in self._vm.processes_rows:
            label = QLabel(row)
            label.setObjectName("TelemetryCaption")
            label.setWordWrap(False)
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

        outer = QVBoxLayout(self._metrics_host)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(6)

        if mode == "side":
            for item in items:
                widget = _HorizontalMetric(item)
                self._metric_widgets.append(widget)
                outer.addWidget(widget)
            outer.addStretch(1)
            self._splitter.setSizes([460, 590])
            return

        row = QWidget()
        row.setObjectName("TelemetryMetricsRow")
        row.setProperty("transparentBg", True)
        row.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        row.setMinimumHeight(154)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        for item in items:
            widget = _VerticalMetric(item)
            self._metric_widgets.append(widget)
            layout.addWidget(widget, 0, Qt.AlignCenter)
        outer.addStretch(1)
        outer.addWidget(row, 0, Qt.AlignCenter)
        outer.addStretch(1)
        self._splitter.setSizes([470, 590])

    def _update_metric_widgets(self) -> None:
        items = self._to_items(self._vm.metric_items())
        if len(items) != len(self._metric_widgets):
            self._rebuild(self._mode or "bottom")
            return
        for widget, item in zip(self._metric_widgets, items, strict=True):
            widget.update_item(item)
