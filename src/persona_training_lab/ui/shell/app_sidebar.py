from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout

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
        self._sync_accent_from_app()

    def add_navigation_item(self, screen_id: str, icon_text: str, title: str) -> NavButton:
        existing = self._buttons.get(screen_id)
        if existing is not None:
            return existing

        container = self.findChild(QFrame, "SidebarNav")
        layout = container.layout() if container is not None else None
        if not isinstance(layout, QVBoxLayout):
            raise RuntimeError("Не найден контейнер основной навигации SidebarNav.")

        button = NavButton(screen_id, icon_text, title)
        button.clicked.connect(lambda _checked=False, sid=screen_id: self._select_screen(sid))
        insert_at = max(0, layout.count() - 1)
        layout.insertWidget(insert_at, button)
        self._buttons[screen_id] = button
        return button
