from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import (
    QHideEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyleOptionFrame,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.panels.localization import text as panel_text
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.telemetry import TelemetryViewModel


_STATUS_KEYS: dict[str, str] = {
    "normal": "panel.telemetry.status.normal",
    "high_load": "panel.telemetry.status.high_load",
    "gpu_unavailable": "panel.telemetry.status.gpu_unavailable",
    "processes_unavailable": "panel.telemetry.status.processes_unavailable",
    "active": "panel.telemetry.status.active",
    "refresh_failed": "panel.telemetry.status.refresh_failed",
}


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
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._fill_probe = QFrame(self)
        self._fill_probe.setObjectName("TelemetryBarFill")
        self._fill_probe.hide()

    def set_value(self, value: int) -> None:
        self._value = max(0, min(100, value))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        opt = QStyleOptionFrame()
        opt.initFrom(self)
        opt.rect = self.rect()
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget,
            opt,
            painter,
            self,
        )

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
        self._fill_probe.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget,
            fill_opt,
            painter,
            self._fill_probe,
        )
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

        layout.addWidget(track, 0, Qt.AlignmentFlag.AlignHCenter)
        caption = QLabel(item.short_label)
        caption.setObjectName("TelemetryChip")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setMinimumWidth(42)
        caption.setFixedHeight(24)
        layout.addWidget(caption, 0, Qt.AlignmentFlag.AlignHCenter)

        value_label = QLabel(item.value_text)
        value_label.setObjectName("TelemetryCaption")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        self._track = track
        self._caption = caption
        self._value_label = value_label

    def set_item(self, item: TelemetryItem) -> None:
        self.setToolTip(item.tooltip)
        self._track.set_value(item.value)
        self._caption.setText(item.short_label)
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
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self._label = label
        self._track = track
        self._value_label = value_label

    def set_item(self, item: TelemetryItem) -> None:
        self.setToolTip(item.tooltip)
        self._label.setText(item.full_label)
        self._track.set_value(item.value)
        self._value_label.setText(item.value_text)


class TelemetryPanel(QFrame):
    def __init__(
        self,
        view_model: TelemetryViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._vm = view_model
        self._localization = localization
        self._items = self._to_items()
        self._mode: str | None = None
        self._refresh_pending = False
        self._metrics_widgets: list[_VerticalMetric | _HorizontalMetric] = []
        self._metrics_layout: QVBoxLayout | QHBoxLayout | None = None
        self._metrics_viewport: QWidget | None = None
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(30_000)
        self._auto_refresh_timer.timeout.connect(self._on_auto_refresh)
        self._dock_widget: QDockWidget | None = None

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 14, 14, 14)
        self._root.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._title = QLabel(self._status_title())
        title_row.addWidget(self._title)
        self._subtitle = QLabel(self._status_subtitle())
        self._subtitle.setObjectName("MutedText")
        title_row.addWidget(
            self._subtitle,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        title_row.addStretch(1)
        self._refresh_btn = QPushButton(
            self._text("panel.telemetry.refresh")
        )
        self._refresh_btn.setObjectName("SecondaryButton")
        self._refresh_btn.clicked.connect(self._on_refresh)
        title_row.addWidget(self._refresh_btn)
        self._root.addLayout(title_row)

        self._error = QLabel(self._status_error())
        self._error.setObjectName("MutedText")
        self._error.setVisible(bool(self._error.text().strip()))
        self._root.addWidget(self._error)

        body_row = QHBoxLayout()
        body_row.setSpacing(16)
        self._root.addLayout(body_row, 1)

        self._content = QWidget()
        self._content.setObjectName("TelemetryMetricsHost")
        self._content.setProperty("transparentBg", True)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)
        body_row.addWidget(self._content, 0)

        processes_shell = QFrame()
        processes_shell.setObjectName("PanelCardSoft")
        processes_shell.setMinimumWidth(340)
        processes_shell.setMaximumWidth(460)
        processes_shell.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        processes_shell_layout = QVBoxLayout(processes_shell)
        processes_shell_layout.setContentsMargins(10, 10, 10, 10)
        processes_shell_layout.setSpacing(8)

        self._processes_header = QLabel(
            self._text("panel.telemetry.processes")
        )
        self._processes_header.setObjectName("TelemetryChip")
        processes_shell_layout.addWidget(self._processes_header)

        self._processes_scroll = QScrollArea()
        self._processes_scroll.setObjectName("TelemetryProcessesScroll")
        self._processes_scroll.setWidgetResizable(True)
        self._processes_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._processes_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._processes_scroll.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        self._processes_scroll.viewport().setObjectName(
            "TelemetryProcessesViewport"
        )
        apply_scrollbar_style(self._processes_scroll)

        self._processes_container = QWidget()
        self._processes_container.setObjectName(
            "TelemetryProcessesContainer"
        )
        self._processes_container.setProperty("transparentBg", True)
        self._processes = QVBoxLayout(self._processes_container)
        self._processes.setContentsMargins(0, 0, 10, 0)
        self._processes.setSpacing(6)
        self._processes.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._processes_scroll.setWidget(self._processes_container)
        processes_shell_layout.addWidget(self._processes_scroll, 1)
        processes_shell_layout.setStretch(1, 1)
        body_row.addWidget(processes_shell, 0)
        body_row.addStretch(1)

        self._refresh_processes()
        self._rebuild("bottom")
        self._auto_refresh_timer.start()
        if localization is not None:
            localization.language_changed.connect(self._on_language_changed)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        desired = (
            "side"
            if self.width() < max(460, self.height() * 0.72)
            else "bottom"
        )
        if desired != self._mode:
            self._rebuild(desired)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._ensure_dock_binding()
        self._apply_floating_size_policy()
        if not self._auto_refresh_timer.isActive():
            self._auto_refresh_timer.start()
        self._on_auto_refresh()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        super().hideEvent(event)
        self._auto_refresh_timer.stop()

    def _ensure_dock_binding(self) -> None:
        if self._dock_widget is not None:
            return
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QDockWidget):
                self._dock_widget = parent
                self._dock_widget.topLevelChanged.connect(
                    lambda _floating: self._apply_floating_size_policy()
                )
                break
            parent = parent.parentWidget()

    def _apply_floating_size_policy(self) -> None:
        if self._dock_widget is None:
            return
        if self._dock_widget.isFloating():
            fixed = QSize(760, 280)
            self._dock_widget.setMinimumSize(fixed)
            self._dock_widget.setMaximumSize(fixed)
            self._dock_widget.resize(fixed)
        else:
            self._dock_widget.setMinimumSize(QSize(0, 0))
            self._dock_widget.setMaximumSize(QSize(16777215, 16777215))

    def _to_items(self) -> list[TelemetryItem]:
        snapshot = self._vm.snapshot
        if snapshot is None:
            return []

        cpu_tooltip = self._text(
            "panel.telemetry.cpu_tooltip",
            status=self._status_text(snapshot.cpu_status_code),
            value=f"{snapshot.cpu_percent:.1f}%",
            cores=snapshot.cpu_logical_cores,
        )
        ram_text = (
            f"{self._format_bytes(snapshot.ram_used_bytes)} / "
            f"{self._format_bytes(snapshot.ram_total_bytes)}"
        )
        if (
            snapshot.vram_used_mb is not None
            and snapshot.vram_total_mb is not None
        ):
            vram_percent = int(
                round(
                    (
                        snapshot.vram_used_mb
                        / max(snapshot.vram_total_mb, 1.0)
                    )
                    * 100
                )
            )
            vram_text = (
                f"{snapshot.vram_used_mb:.0f} / "
                f"{snapshot.vram_total_mb:.0f} MB"
            )
        else:
            vram_percent = 0
            vram_text = self._text(
                "panel.telemetry.status.gpu_unavailable"
            )

        if snapshot.gpu_temperature_c is None:
            temp_percent = 0
            temp_text = "—"
        else:
            temp_percent = int(
                min(100, round(snapshot.gpu_temperature_c))
            )
            temp_text = f"{snapshot.gpu_temperature_c:.0f}°C"

        proc_value = (
            int(min(100, round(snapshot.processes[0].cpu_percent)))
            if snapshot.processes
            else 0
        )

        return [
            TelemetryItem(
                short_label="CPU",
                full_label="CPU",
                value=int(round(snapshot.cpu_percent)),
                tooltip=cpu_tooltip,
                value_text=f"{snapshot.cpu_percent:.1f}%",
            ),
            TelemetryItem(
                short_label="RAM",
                full_label="RAM",
                value=int(round(snapshot.ram_percent)),
                tooltip=ram_text,
                value_text=f"{snapshot.ram_percent:.1f}%",
            ),
            TelemetryItem(
                short_label="GPU",
                full_label="GPU",
                value=int(round(snapshot.gpu_util_percent or 0.0)),
                tooltip=self._status_text(snapshot.gpu_status_code),
                value_text=(
                    f"{snapshot.gpu_util_percent:.1f}%"
                    if snapshot.gpu_util_percent is not None
                    else "—"
                ),
            ),
            TelemetryItem(
                short_label="VRAM",
                full_label="VRAM",
                value=vram_percent,
                tooltip=vram_text,
                value_text=vram_text,
            ),
            TelemetryItem(
                short_label=self._text(
                    "panel.telemetry.metric.temperature.short"
                ),
                full_label=self._text(
                    "panel.telemetry.metric.temperature.full"
                ),
                value=temp_percent,
                tooltip=temp_text,
                value_text=temp_text,
            ),
            TelemetryItem(
                short_label=self._text(
                    "panel.telemetry.metric.process.short"
                ),
                full_label=self._text(
                    "panel.telemetry.metric.process.full"
                ),
                value=proc_value,
                tooltip=self._status_text(
                    snapshot.processes_status_code
                ),
                value_text=(
                    f"{proc_value}%" if snapshot.processes else "—"
                ),
            ),
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
            self._refresh_btn.setText(
                self._text("panel.telemetry.refreshing")
            )
        QTimer.singleShot(0, self._finish_refresh)

    def _finish_refresh(self) -> None:
        try:
            self._vm.refresh()
            self._title.setText(self._status_title())
            self._subtitle.setText(self._status_subtitle())
            self._error.setText(self._status_error())
            self._error.setVisible(bool(self._error.text().strip()))
            self._items = self._to_items()
            self._refresh_processes()
            self._update_metric_widgets()
        finally:
            self._refresh_btn.setText(
                self._text("panel.telemetry.refresh")
            )
            self._refresh_btn.setEnabled(True)
            self._refresh_pending = False

    def _update_metric_widgets(self) -> None:
        if len(self._metrics_widgets) != len(self._items):
            self._rebuild(self._mode or "bottom")
            return
        for widget, item in zip(self._metrics_widgets, self._items):
            widget.set_item(item)

    def _refresh_processes(self) -> None:
        while self._processes.count():
            layout_item = self._processes.takeAt(0)
            if layout_item is None:
                continue
            widget = layout_item.widget()
            if widget is not None:
                widget.deleteLater()

        snapshot = self._vm.snapshot
        if snapshot is None or not snapshot.processes:
            label = QLabel(
                self._text(
                    "panel.telemetry.status.processes_unavailable"
                )
            )
            label.setWordWrap(True)
            self._processes.addWidget(label)
            return

        for process in snapshot.processes:
            label = QLabel(
                self._text(
                    "panel.telemetry.process_row",
                    pid=process.pid,
                    name=process.name,
                    cpu=f"{process.cpu_percent:.1f}",
                    ram=f"{process.ram_percent:.1f}",
                )
            )
            label.setWordWrap(True)
            self._processes.addWidget(label)

    def _rebuild(self, mode: str) -> None:
        self._mode = mode

        if self._metrics_viewport is not None:
            self._content_layout.removeWidget(self._metrics_viewport)
            self._metrics_viewport.hide()
            self._metrics_viewport.deleteLater()
            self._metrics_viewport = None

        self._metrics_layout = None
        self._metrics_widgets = []

        viewport = QWidget()
        viewport.setObjectName("TelemetryMetricsViewport")
        viewport.setProperty("transparentBg", True)

        if mode == "side":
            side_layout = QVBoxLayout(viewport)
            side_layout.setContentsMargins(0, 0, 0, 0)
            side_layout.setSpacing(12)
            self._metrics_layout = side_layout
            for item in self._items:
                horizontal_metric = _HorizontalMetric(item)
                self._metrics_widgets.append(horizontal_metric)
                side_layout.addWidget(horizontal_metric)
            alignment = Qt.AlignmentFlag.AlignTop
        else:
            bottom_layout = QHBoxLayout(viewport)
            bottom_layout.setContentsMargins(0, 0, 0, 0)
            bottom_layout.setSpacing(10)
            self._metrics_layout = bottom_layout
            for item in self._items:
                vertical_metric = _VerticalMetric(item)
                self._metrics_widgets.append(vertical_metric)
                bottom_layout.addWidget(vertical_metric)
            alignment = (
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )

        self._metrics_viewport = viewport
        self._content_layout.addWidget(viewport, 0, alignment)

    def _on_language_changed(self, _locale: str) -> None:
        self._title.setText(self._status_title())
        self._subtitle.setText(self._status_subtitle())
        self._error.setText(self._status_error())
        self._error.setVisible(bool(self._error.text().strip()))
        self._processes_header.setText(
            self._text("panel.telemetry.processes")
        )
        self._refresh_btn.setText(
            self._text(
                "panel.telemetry.refreshing"
                if self._refresh_pending
                else "panel.telemetry.refresh"
            )
        )
        self._items = self._to_items()
        self._refresh_processes()
        self._update_metric_widgets()

    def _status_title(self) -> str:
        snapshot = self._vm.snapshot
        code = snapshot.status_code if snapshot is not None else "active"
        return self._status_text(code)

    def _status_subtitle(self) -> str:
        snapshot = self._vm.snapshot
        if snapshot is None:
            return self._text("panel.telemetry.status.active")
        return self._text(
            "panel.telemetry.updated_at",
            time=snapshot.last_updated_at,
        )

    def _status_error(self) -> str:
        snapshot = self._vm.snapshot
        if snapshot is None or not snapshot.error_code:
            return ""
        key = _STATUS_KEYS.get(snapshot.error_code)
        return self._text(key) if key is not None else snapshot.error_message

    def _status_text(self, code: str) -> str:
        key = _STATUS_KEYS.get(code)
        if key is None:
            return code.replace("_", " ").title()
        return self._text(key)

    def _text(self, key: str, **values: object) -> str:
        return panel_text(
            self._localization,
            key,
            **values,
        )

    @staticmethod
    def _format_bytes(value: int) -> str:
        if value <= 0:
            return "0 GB"
        gb = value / (1024**3)
        return f"{gb:.1f} GB"
