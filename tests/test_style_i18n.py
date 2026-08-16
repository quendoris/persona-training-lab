from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
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
    assert screen._language_label.text() == "Interface language"
    assert screen._language_box.currentData() == "en-US"
    assert screen._language_box.itemText(
        screen._language_box.findData("ru-RU")
    ) == "Русский"
    assert screen._language_note.text() == (
        "The language changes without restarting the application."
    )
    assert screen._theme_box.currentData() == "velvet"
    assert screen._theme_box.currentText() == "Velvet"
    assert screen._accent_box.currentData() == "cyan"
    assert screen._accent_box.currentText() == "Cyan"
    assert screen._apply_button.text() == "Apply appearance"

    screen._language_box.setCurrentIndex(
        screen._language_box.findData("ru-RU")
    )

    assert manager.locale == "ru-RU"
    assert screen._controls.title_label.text() == "Оформление"
    assert screen._language_label.text() == "Язык интерфейса"
    assert screen._language_box.currentData() == "ru-RU"
    assert screen._language_note.text() == (
        "Язык меняется без перезапуска приложения."
    )
    assert screen._theme_box.currentData() == "velvet"
    assert screen._theme_box.currentText() == "Velvet"
    assert screen._accent_box.currentData() == "cyan"
    assert screen._accent_box.currentText() == "Бирюзовый"
    assert screen._apply_button.text() == "Применить оформление"

    screen._language_box.setCurrentIndex(
        screen._language_box.findData("en-US")
    )

    assert manager.locale == "en-US"
    assert screen._theme_box.currentData() == "velvet"
    assert screen._accent_box.currentData() == "cyan"
    assert screen._accent_box.currentText() == "Cyan"

    screen.deleteLater()
    app.processEvents()


def test_locale_metadata_controls_application_layout_direction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = {"label": "Label"}
    for locale, native_name, direction in (
        ("ru-RU", "Русский", "ltr"),
        ("en-US", "English", "ltr"),
        ("ar-SA", "العربية", "rtl"),
    ):
        payload = {
            "meta": {
                "schema": 1,
                "locale": locale,
                "name": locale,
                "native_name": native_name,
                "direction": direction,
            },
            "messages": messages,
        }
        (tmp_path / f"{locale}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=tmp_path,
    )
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)

    manager.set_locale("ar-SA", persist=False)
    assert app.layoutDirection() is Qt.LayoutDirection.RightToLeft

    manager.set_locale("en-US", persist=False)
    assert app.layoutDirection() is Qt.LayoutDirection.LeftToRight
