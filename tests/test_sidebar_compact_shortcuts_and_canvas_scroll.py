from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.agents.screen_contextual import AgentsScreen
from persona_training_lab.ui.panels.inspector_panel import InspectorPanel
from persona_training_lab.ui.shell.app_sidebar import Sidebar
from persona_training_lab.ui.shell.sidebar import NavButton


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_sidebar_shortcut_hint_does_not_expand_visible_title() -> None:
    app = _app()
    button = NavButton("agents", "АГ", "Агенты")
    fake_sidebar = SimpleNamespace(_buttons={"agents": button})

    Sidebar.set_navigation_shortcut_hint(fake_sidebar, "agents", "Alt+G")

    assert button.text() == "Агенты"
    assert button.property("navigation_shortcut") == "Alt+G"
    assert "Alt+G" in button.toolTip()
    button.deleteLater()
    app.processEvents()


def test_brand_panels_button_moves_beneath_title_in_same_row() -> None:
    app = _app()
    brand = QFrame()
    brand_layout = QVBoxLayout(brand)
    top_row = QHBoxLayout()
    badge = QLabel()
    title = QLabel("Persona Training Lab")
    title.setObjectName("SidebarTitle")
    top_row.addWidget(badge)
    top_row.addWidget(title)
    brand_layout.addLayout(top_row)
    toggle = QPushButton("панели")
    brand_layout.addWidget(toggle)
    fake_sidebar = SimpleNamespace(
        _brand_badge=badge,
        _window_toggle=toggle,
    )

    Sidebar._compact_brand_panel(fake_sidebar)

    assert brand_layout.count() == 1
    identity = top_row.itemAt(1).widget()
    assert isinstance(identity, QWidget)
    identity_layout = identity.layout()
    assert isinstance(identity_layout, QVBoxLayout)
    assert identity_layout.indexOf(title) >= 0
    assert identity_layout.indexOf(toggle) >= 0
    brand.deleteLater()
    app.processEvents()


def test_inspector_shows_current_workspace_shortcut() -> None:
    app = _app()
    panel = InspectorPanel()

    panel.set_context("agents")
    panel.set_navigation_shortcut("agents", "Alt+G")

    assert panel._shortcut.text() == "Alt+G · открыть «Агенты»"
    panel.deleteLater()
    app.processEvents()


class _FakeBar:
    def __init__(self, value: int) -> None:
        self._value = value

    def value(self) -> int:
        return self._value


class _FakeScroll:
    def __init__(self, horizontal: int, vertical: int) -> None:
        self._horizontal = _FakeBar(horizontal)
        self._vertical = _FakeBar(vertical)

    def horizontalScrollBar(self) -> _FakeBar:
        return self._horizontal

    def verticalScrollBar(self) -> _FakeBar:
        return self._vertical


def test_fast_zoom_anchor_is_applied_synchronously() -> None:
    corrections: list[tuple[int, int]] = []
    fake_screen = SimpleNamespace(
        _graph_scroll=_FakeScroll(200, 300),
        _apply_workspace_scroll_shift=lambda h, v: corrections.append((h, v)),
    )

    AgentsScreen._on_graph_zoom_anchor(
        fake_screen,
        QPointF(100.0, 50.0),
        1.0,
        2.0,
    )

    assert corrections == [(300, 350)]


def test_workspace_origin_shift_is_applied_synchronously() -> None:
    corrections: list[tuple[int, int]] = []
    fake_screen = SimpleNamespace(
        _graph_scroll=_FakeScroll(200, 300),
        _apply_workspace_scroll_shift=lambda h, v: corrections.append((h, v)),
    )

    AgentsScreen._on_graph_workspace_origin_shift(
        fake_screen,
        QPointF(12.4, -8.6),
    )

    assert corrections == [(212, 291)]
