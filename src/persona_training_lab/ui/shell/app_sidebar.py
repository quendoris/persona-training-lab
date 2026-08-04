from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from persona_training_lab.ui.shell.sidebar import NavButton, Sidebar as _BaseSidebar


APPLICATION_NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("keybindings", "КЛ", "Назначения клавиш"),
)


class Sidebar(_BaseSidebar):
    """Application navigation additions layered on the stable base sidebar."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
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
        button = self._buttons.get(screen_id)
        if button is None:
            return
        title = str(
            button.property("navigation_base_title")
            or button.text().split("  ·  ", 1)[0]
        )
        button.setProperty("navigation_base_title", title)
        button.setText(f"{title}  ·  {shortcut}")
        button.setToolTip(f"Открыть вкладку · {shortcut}")

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

    def _find_workflow_layout(self) -> QVBoxLayout | None:
        for label in self.findChildren(QLabel):
            if label.text() != "Активные процессы":
                continue
            parent = label.parentWidget()
            layout = parent.layout() if parent is not None else None
            if isinstance(layout, QVBoxLayout):
                return layout
        return None
