from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.shell.sidebar import (
    NavButton,
    Sidebar as _BaseSidebar,
    base_text,
)


APPLICATION_NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("keybindings", "КЛ", "nav.keybindings"),
)

NAVIGATION_KEYS: dict[str, str] = {
    "dashboard": "nav.dashboard",
    "profiles": "nav.profiles",
    "agents": "nav.agents",
    "datasets": "nav.datasets",
    "training": "nav.training",
    "snapshots": "nav.snapshots",
    "tests": "nav.tests",
    "analysis": "nav.analysis",
    "style": "nav.style",
    "docs": "nav.docs",
    "keybindings": "nav.keybindings",
}


class Sidebar(_BaseSidebar):
    """Application navigation additions layered on the stable base sidebar."""

    def __init__(self, *args, **kwargs) -> None:
        self._localization: LocalizationManager | None = kwargs.pop(
            "localization",
            None,
        )
        super().__init__(*args, **kwargs)
        self._compact_brand_panel()
        for screen_id, icon_text, title_key in APPLICATION_NAV_ITEMS:
            self.add_navigation_item(screen_id, icon_text, title_key)
        self._workflow_layout = self._find_workflow_layout()
        self._bind_localized_shell()
        self.set_active_workflows(())
        self._sync_accent_from_app()
        if self._localization is not None:
            self._localization.language_changed.connect(
                self._refresh_localized_shell
            )

    def add_navigation_item(
        self,
        screen_id: str,
        icon_text: str,
        title_key: str,
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

        button = NavButton(
            screen_id,
            icon_text,
            self._text(title_key),
        )
        button.setProperty("navigation_key", title_key)
        button.setProperty("navigation_base_title", button.text())
        button.clicked.connect(
            lambda _checked=False, sid=screen_id: self._select_screen(sid)
        )
        insert_at = max(0, layout.count() - 1)
        layout.insertWidget(insert_at, button)
        self._buttons[screen_id] = button
        if self._localization is not None:
            self._localization.bind_text(button, title_key)
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
        button.setProperty("navigation_shortcut", shortcut)
        refresh = getattr(self, "_refresh_navigation_button", None)
        if callable(refresh):
            refresh(button)
            return

        # Keep this helper independently testable and safe for compatibility
        # adapters that only provide the button registry.
        title = str(
            button.property("navigation_base_title")
            or button.text().split("  ·  ", 1)[0]
        )
        button.setProperty("navigation_base_title", title)
        button.setText(title)
        resolver = getattr(self, "_text", None)
        button.setToolTip(
            resolver(
                "nav.open_tooltip",
                title=title,
                shortcut=shortcut,
            )
            if callable(resolver)
            else base_text(
                "nav.open_tooltip",
                title=title,
                shortcut=shortcut,
            )
        )

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
            pill = QLabel(self._text("operations.none_active"))
            pill.setObjectName("WorkflowPill")
            if self._localization is not None:
                self._localization.bind_text(pill, "operations.none_active")
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

        text_resolver = getattr(self, "_text", None)
        toggle.setText(
            text_resolver("shell.panels.decorated")
            if callable(text_resolver)
            else base_text("shell.panels.decorated")
        )
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

        # The compact reparenting changes sibling stacking. Keep the control and
        # its accent outline above transparent identity/title layers.
        identity.raise_()
        toggle.raise_()

    def _find_workflow_layout(self) -> QVBoxLayout | None:
        heading = getattr(self, "_workflow_title", None)
        if not isinstance(heading, QLabel):
            return None
        parent = heading.parentWidget()
        layout = parent.layout() if parent is not None else None
        return layout if isinstance(layout, QVBoxLayout) else None

    def _bind_localized_shell(self) -> None:
        localization = self._localization
        if localization is None:
            return

        title = self.findChild(QLabel, "SidebarTitle")
        if title is not None:
            localization.bind_text(title, "app.name")
            localization.bind_tooltip(title, "app.name")
        localization.bind_text(
            self._window_toggle,
            "shell.panels.decorated",
        )
        localization.bind_text(self._theme_title, "shell.themes")
        localization.bind_text(self._scale_title, "shell.scale")
        localization.bind_text(
            self._reset_scale,
            "shell.scale.auto_button",
        )
        localization.bind_text(
            self._workflow_title,
            "shell.active_processes",
        )

        for screen_id, button in self._buttons.items():
            key = NAVIGATION_KEYS.get(screen_id)
            if key is None:
                continue
            button.setProperty("navigation_key", key)
            localization.bind_text(button, key)
            self._refresh_navigation_button(button)

    def _refresh_localized_shell(self, _locale: str) -> None:
        for button in self._buttons.values():
            self._refresh_navigation_button(button)
        self._toggle_theme_panel(self._theme_toggle.isChecked())
        self._toggle_scale_panel(self._scale_toggle.isChecked())
        self._sync_scale_controls()

    def _refresh_navigation_button(self, button: NavButton) -> None:
        key = str(button.property("navigation_key") or "")
        if key:
            title = self._text(key)
            button.setText(title)
            button.setProperty("navigation_base_title", title)
        else:
            title = str(
                button.property("navigation_base_title")
                or button.text()
            )
        shortcut = str(button.property("navigation_shortcut") or "")
        if shortcut:
            button.setToolTip(
                self._text(
                    "nav.open_tooltip",
                    title=title,
                    shortcut=shortcut,
                )
            )
        else:
            button.setToolTip(title)

    def _text(self, key: str, **values: object) -> str:
        if self._localization is None:
            return base_text(key, **values)
        return self._localization.text(key, **values)
