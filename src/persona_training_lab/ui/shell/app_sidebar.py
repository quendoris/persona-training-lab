from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.shell.sidebar import NavButton, Sidebar as _BaseSidebar


APPLICATION_NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("keybindings", "КЛ", "Назначения клавиш"),
)


class Sidebar(_BaseSidebar):
    """Application navigation additions layered on the stable base sidebar."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._compact_brand_panel()
        for screen_id, icon_text, title in APPLICATION_NAV_ITEMS:
            self.add_navigation_item(screen_id, icon_text, title)
        self._workflow_layout = self._find_workflow_layout()
        self.set_active_workflows(())
        self._sync_accent_from_app()

    def add_navigation_item(
        self,
        screen_id: str,
        icon_text: str,
        title: str,
    ) -> NavButton:
        existing = self._buttons.get(screen_id)
        if existing is not None:
            return existing

        container = self.findChild(QFrame, "SidebarNav")
        layout = container.layout() if container is not None else None
        if not isinstance(layout, QVBoxLayout):
            raise RuntimeError(
                "Не найден контейнер основной навигации SidebarNav."
            )

        button = NavButton(screen_id, icon_text, title)
        button.clicked.connect(
            lambda _checked=False, sid=screen_id: self._select_screen(sid)
        )
        insert_at = max(0, layout.count() - 1)
        layout.insertWidget(insert_at, button)
        self._buttons[screen_id] = button
        return button

    def set_navigation_shortcut_hint(
        self,
        screen_id: str,
        shortcut: str,
    ) -> None:
        """Keep navigation compact; expose shortcuts through tooltip/inspector."""

        button = self._buttons.get(screen_id)
        if button is None:
            return
        title = str(
            button.property("navigation_base_title")
            or button.text().split("  ·  ", 1)[0]
        )
        button.setProperty("navigation_base_title", title)
        button.setProperty("navigation_shortcut", shortcut)
        button.setText(title)
        button.setToolTip(f"Открыть вкладку «{title}» · {shortcut}")

    def set_active_workflows(self, items) -> None:
        layout = self._workflow_layout
        if layout is None:
            return
        while layout.count() > 1:
            item = layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        values = tuple(str(item).strip() for item in items if str(item).strip())
        if not values:
            pill = QLabel("Нет активных операций")
            pill.setObjectName("WorkflowPill")
            layout.addWidget(pill)
            return
        for text in values:
            pill = QLabel(text)
            pill.setObjectName("WorkflowPill")
            pill.setToolTip(text)
            layout.addWidget(pill)

    def _compact_brand_panel(self) -> None:
        """Place the panels menu beneath the title instead of below the card."""

        badge = self._brand_badge
        toggle = self._window_toggle
        if badge is None:
            return
        brand = badge.parentWidget()
        brand_layout = brand.layout() if brand is not None else None
        if not isinstance(brand_layout, QVBoxLayout):
            return
        top_item = brand_layout.itemAt(0)
        top_row = top_item.layout() if top_item is not None else None
        if not isinstance(top_row, QHBoxLayout):
            return
        title = brand.findChild(QLabel, "SidebarTitle")
        if title is None:
            return

        top_row.removeWidget(title)
        brand_layout.removeWidget(toggle)

        identity = QWidget(brand)
        identity.setProperty("transparentBg", True)
        identity_layout = QVBoxLayout(identity)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(5)
        identity_layout.addWidget(title)

        toggle.setText("──── панели ────")
        toggle.setMinimumHeight(28)
        toggle.setMaximumHeight(28)
        toggle.setMinimumWidth(148)
        toggle.setMaximumWidth(172)
        identity_layout.addWidget(toggle)
        identity_layout.addStretch(1)

        top_row.addWidget(identity, 1)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(12)
        brand_layout.setContentsMargins(14, 12, 14, 12)
        brand_layout.setSpacing(0)

    def _find_workflow_layout(self) -> QVBoxLayout | None:
        for label in self.findChildren(QLabel):
            if label.text() != "Активные процессы":
                continue
            parent = label.parentWidget()
            layout = parent.layout() if parent is not None else None
            if isinstance(layout, QVBoxLayout):
                return layout
        return None
