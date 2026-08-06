from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QLabel,
    QMenu,
)

from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.shell.app_sidebar import Sidebar
from persona_training_lab.ui.shell.status_bar import AppStatusBar


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


class _StyleViewModel:
    def __init__(self) -> None:
        self.preferences = {
            "theme": "velvet",
            "accent_palette": "cyan",
            "button_style_preset": "soft_glow",
            "ui_scale": "auto",
            "language": "en-US",
        }

    def load(self) -> dict[str, str]:
        return dict(self.preferences)

    def save(
        self,
        theme: str,
        accent_palette: str,
        button_style_preset: str,
    ) -> None:
        self.preferences.update(
            theme=theme,
            accent_palette=accent_palette,
            button_style_preset=button_style_preset,
        )

    def save_ui_scale(self, ui_scale: str) -> None:
        self.preferences["ui_scale"] = ui_scale


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _labels(sidebar: Sidebar) -> set[str]:
    return {label.text() for label in sidebar.findChildren(QLabel)}


def test_sidebar_shell_switches_language_without_widget_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    persisted: list[str] = []
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
        persist_locale=persisted.append,
    )
    sidebar = Sidebar(
        style_vm=_StyleViewModel(),
        on_apply_theme=lambda _theme, _accent: None,
        active_workflows=[],
        localization=manager,
    )
    dashboard_button = sidebar._buttons["dashboard"]
    agents_button = sidebar._buttons["agents"]
    sidebar.set_navigation_shortcut_hint("agents", "Alt+A")

    assert dashboard_button.text() == "Dashboard"
    assert agents_button.text() == "Agents"
    assert agents_button.toolTip() == "Open the “Agents” tab · Alt+A"
    assert sidebar._window_toggle.text() == "──── panels ────"
    assert sidebar._theme_title.text() == "Themes"
    assert sidebar._scale_title.text() == "Scale"
    assert sidebar._theme_toggle.text() == "Show"
    assert sidebar._scale_toggle.text() == "Show"
    assert sidebar._reset_scale.text() == "Auto"
    assert sidebar._scale_value.text().startswith("Auto ")
    assert sidebar._scale_hint.text() == "Automatic based on screen height"
    assert "Active processes" in _labels(sidebar)
    assert "No active operations" in _labels(sidebar)

    sidebar._theme_toggle.setChecked(True)
    sidebar._toggle_theme_panel(True)
    sidebar._scale_toggle.setChecked(True)
    sidebar._toggle_scale_panel(True)
    assert sidebar._theme_toggle.text() == "Hide"
    assert sidebar._scale_toggle.text() == "Hide"

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU")

    assert sidebar._buttons["dashboard"] is dashboard_button
    assert dashboard_button.text() == "Панель"
    assert agents_button.text() == "Агенты"
    assert agents_button.toolTip() == "Открыть вкладку «Агенты» · Alt+A"
    assert sidebar._window_toggle.text() == "──── панели ────"
    assert sidebar._theme_title.text() == "Темы"
    assert sidebar._scale_title.text() == "Масштаб"
    assert sidebar._theme_toggle.text() == "скрыть"
    assert sidebar._scale_toggle.text() == "скрыть"
    assert sidebar._reset_scale.text() == "авто"
    assert sidebar._scale_value.text().startswith("авто ")
    assert sidebar._scale_hint.text() == "Авто по высоте экрана"
    assert "Активные процессы" in _labels(sidebar)
    assert "Нет активных операций" in _labels(sidebar)
    assert persisted == ["ru-RU"]

    sidebar._apply_scale_live(111)
    assert sidebar._scale_value.text() == "111%"
    assert sidebar._scale_hint.text() == "Применяется сразу"

    sidebar.deleteLater()
    app.processEvents()


def test_shell_titles_and_ready_status_switch_without_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    menu = QMenu()
    dock = QDockWidget()
    status = AppStatusBar(manager)
    manager.bind_title(menu, "shell.panels")
    manager.bind_window_title(dock, "dock.inspector")

    assert menu.title() == "Panels"
    assert dock.windowTitle() == "Inspector"
    assert status._left.text() == "Ready"

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU", persist=False)

    assert menu.title() == "Панели"
    assert dock.windowTitle() == "Инспектор"
    assert status._left.text() == "Готово"

    menu.deleteLater()
    dock.deleteLater()
    status.deleteLater()
    app.processEvents()
