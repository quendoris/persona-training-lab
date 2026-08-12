from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.application.operations_center import (
    OperationsCenterItem,
    OperationsCenterService,
)
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.panels.localization import (
    item_focus,
    item_status,
    item_summary,
    item_title,
    text as panel_text,
)
from persona_training_lab.ui.themes.manager import apply_scrollbar_style


class _ActivityRow(QPushButton):
    navigate_requested = Signal(str, str)

    def __init__(
        self,
        item: OperationsCenterItem,
        localization: LocalizationManager | None,
    ) -> None:
        super().__init__()
        self._item = item
        self.setObjectName("PanelCardSoft")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(64)
        tooltip = panel_text(localization, "operations.open_related")
        self.setToolTip(
            tooltip
            + (f" · {item.correlation_id}" if item.correlation_id else "")
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        title = QLabel(item_title(item, localization))
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        title.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        note = make_muted_label(item_summary(item, localization))
        note.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        text_layout.addWidget(title)
        text_layout.addWidget(note)
        layout.addLayout(text_layout, 1)

        tone = (
            "pending"
            if item.severity in {"warning", "error", "critical"}
            else "good"
        )
        status = make_status_label(
            item_status(item, localization),
            tone=tone,
        )
        status.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        layout.addWidget(status, 0, Qt.AlignmentFlag.AlignTop)
        self.clicked.connect(
            lambda: self.navigate_requested.emit(
                item.target_screen,
                item_focus(item, localization),
            )
        )


class ActivityPanel(QFrame):
    navigate_requested = Signal(str, str)

    def __init__(
        self,
        operations_center: OperationsCenterService | None = None,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._operations_center = operations_center
        self._localization = localization
        self._render_signature: tuple[object, ...] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self._title = QLabel(self._text("panel.activity.title"))
        self._title.setObjectName("SectionTitle")
        self._subtitle = make_muted_label(
            self._text("panel.activity.description")
        )
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)

        scroll = QScrollArea()
        scroll.setObjectName("StableScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        apply_scrollbar_style(scroll)

        container = QWidget()
        container.setProperty("transparentBg", True)
        self._rows = QVBoxLayout(container)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(8)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        if localization is not None:
            localization.language_changed.connect(self._on_language_changed)
        self.refresh(force=True)

    def set_service(self, operations_center: OperationsCenterService) -> None:
        self._operations_center = operations_center
        self._render_signature = None
        self.refresh(force=True)

    def showEvent(self, event: QShowEvent) -> None:
        self._timer.start()
        self.refresh(force=True)
        super().showEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def refresh(self, *, force: bool = False) -> None:
        service = self._operations_center
        if service is None:
            signature: tuple[object, ...] = ("disconnected",)
            if not force and signature == self._render_signature:
                return
            self._render_signature = signature
            self._clear_rows()
            self._subtitle.setText(self._text("panel.activity.waiting"))
            self._rows.addWidget(
                make_muted_label(self._text("panel.common.no_source"))
            )
            self._rows.addStretch(1)
            return

        active = service.active_items()
        recent = service.recent_activity(24)
        active_ids = {item.item_id for item in active}
        history = tuple(
            item for item in recent if item.item_id not in active_ids
        )
        signature = (
            tuple(self._item_signature(item) for item in active),
            tuple(self._item_signature(item) for item in history),
        )
        if not force and signature == self._render_signature:
            return
        self._render_signature = signature
        self._clear_rows()
        self._subtitle.setText(
            self._text(
                "panel.activity.summary",
                active=len(active),
                history=len(history),
            )
        )

        if active:
            self._add_section(self._text("panel.activity.now"))
            for item in active:
                self._add_item(item)
        if history:
            self._add_section(self._text("panel.activity.recent"))
            for item in history:
                self._add_item(item)
        if not active and not history:
            self._rows.addWidget(
                make_muted_label(self._text("panel.activity.empty"))
            )
        self._rows.addStretch(1)

    @staticmethod
    def _item_signature(item: OperationsCenterItem) -> tuple[str, ...]:
        return (
            item.item_id,
            item.title,
            item.summary,
            item.status,
            item.severity,
            item.occurred_at,
            item.target_screen,
            item.focus_text,
            item.correlation_id,
            item.operation_kind,
            item.operation_state,
            item.operation_subject,
            item.operation_error,
            item.focus_key,
        )

    def _add_section(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("CardTitle")
        self._rows.addWidget(label)

    def _add_item(self, item: OperationsCenterItem) -> None:
        row = _ActivityRow(item, self._localization)
        row.navigate_requested.connect(self.navigate_requested.emit)
        self._rows.addWidget(row)

    def _clear_rows(self) -> None:
        while self._rows.count():
            item = self._rows.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _on_language_changed(self, _locale: str) -> None:
        self._title.setText(self._text("panel.activity.title"))
        self._render_signature = None
        self.refresh(force=True)

    def _text(self, key: str, **values: object) -> str:
        return panel_text(
            self._localization,
            key,
            **values,
        )
