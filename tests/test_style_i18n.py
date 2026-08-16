from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.style.screen import StyleScreen
from persona_training_lab.ui.themes import manager as theme_manager


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


class _StyleVM:
    def __init__(self) -> None:
        self.saved: list[dict[str, str]] = []

    def load(self) -> dict[str, str]:
        return {
            "theme": "velvet",
            "accent_palette": "cyan",
        }

    def save(self, **values: str) -> None:
        self.saved.append(dict(values))


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_stylesheet_uses_packaged_chevron_asset_without_repo_cwd() -> None:
    stylesheet = theme_manager.build_stylesheet("velvet", "cyan")
    asset = (
        Path(theme_manager.__file__).resolve().parent.parent
        / "assets"
        / "icons"
        / "chevron_down.svg"
    )

    assert asset.is_file()
    assert asset.as_posix() in stylesheet
    assert "url(src/persona_training_lab/" not in stylesheet


def test_style_workspace_switches_language_without_losing_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    vm = _StyleVM()
    screen = StyleScreen(vm, lambda _theme, _accent: None, manager)

    assert screen._controls.title_label.text() == "Appearance"
    assert screen._theme_box.currentData() == "velvet"
    assert screen._theme_box.currentText() == "Velvet"
    assert screen._accent_box.currentData() == "cyan"
    assert screen._accent_box.currentText() == "Cyan"
    assert screen._apply_button.text() == "Apply appearance"

    manager.set_locale("ru-RU", persist=False)

    assert screen._controls.title_label.text() == "Оформление"
    assert screen._theme_box.currentData() == "velvet"
    assert screen._theme_box.currentText() == "Velvet"
    assert screen._accent_box.currentData() == "cyan"
    assert screen._accent_box.currentText() == "Бирюзовый"
    assert screen._apply_button.text() == "Применить оформление"

    manager.set_locale("en-US", persist=False)

    assert screen._theme_box.currentData() == "velvet"
    assert screen._accent_box.currentData() == "cyan"
    assert screen._accent_box.currentText() == "Cyan"

    screen.deleteLater()
    app.processEvents()
