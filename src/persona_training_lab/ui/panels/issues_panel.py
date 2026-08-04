from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
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
from persona_training_lab.ui.themes.manager import apply_scrollbar_style


class _IssueRow(QPushButton):
    navigate_requested = Signal(str, str)

    def __init__(self, item: OperationsCenterItem) -> None:
        super().__init__()
        self.setObjectName("WarningBlock")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(68)
        self.setToolTip(
            "Открыть связанную вкладку"
            + (f" · {item.correlation_id}" if item.correlation_id else "")
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        text = QVBoxLayout()
        text.setSpacing(4)
        title = QLabel(item.title)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        note = make_muted_label(item.summary)
        note.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text.addWidget(title)
        text.addWidget(note)
        layout.addLayout(text, 1)

        badge = make_status_label(item.status, warning=True)
        badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        self.clicked.connect(
            lambda: self.navigate_requested.emit(
                item.target_screen,
                item.focus_text,
            )
        )


class IssuesPanel(QFrame):
    navigate_requested = Signal(str, str)

    def __init__(
        self,
        operations_center: OperationsCenterService | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._operations_center = operations_center

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Проблемы")
        title.setObjectName("SectionTitle")
        self._subtitle = make_muted_label(
            "Восстановимые ошибки и предупреждения без спама в консоль."
        )
        layout.addWidget(title)
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
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def set_service(self, operations_center: OperationsCenterService) -> None:
        self._operations_center = operations_center
        self.refresh()

    def refresh(self) -> None:
        self._clear_rows()
        service = self._operations_center
        if service is None:
            self._subtitle.setText("Ожидание подключения журнала проблем.")
            self._rows.addWidget(make_muted_label("Нет подключённого источника."))
            self._rows.addStretch(1)
            return

        issues = service.issue_items(24)
        self._subtitle.setText(
            "Проблем нет — рабочий контур чист."
            if not issues
            else f"Требуют внимания: {len(issues)}"
        )
        if not issues:
            clean = QFrame()
            clean.setObjectName("PanelCardSoft")
            clean_layout = QVBoxLayout(clean)
            clean_layout.setContentsMargins(12, 10, 12, 10)
            clean_layout.addWidget(
                make_status_label("0 критических проблем", warning=False)
            )
            clean_layout.addWidget(
                make_muted_label(
                    "Новые ошибки появятся здесь с error_id и correlation_id."
                )
            )
            self._rows.addWidget(clean)
        else:
            for item in issues:
                row = _IssueRow(item)
                row.navigate_requested.connect(self.navigate_requested.emit)
                self._rows.addWidget(row)
        self._rows.addStretch(1)

    def _clear_rows(self) -> None:
        while self._rows.count():
            item = self._rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
