from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import render_user_message
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.keybindings.screen import (
    KeyBindingsScreen,
    _MouseGestureDialog,
    _ShortcutCaptureDialog,
)


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _localization(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> LocalizationManager:
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    return manager


def test_keybindings_live_language_preserves_conflicting_draft_and_capture(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    localization = _localization(app, monkeypatch)
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    screen = KeyBindingsScreen(manager, localization)

    assert screen._header.title_label.text() == "Keyboard and mouse bindings"
    assert screen._keyboard_cards["delete_branch"].title_label.text() == (
        "Delete selected branch"
    )
    assert screen._mouse_chips["move_node"].text() == "Right button"

    result = screen._draft.set_sequence("delete_branch", "Ctrl+Z")
    assert result.accepted is True
    screen._refresh_bindings()
    screen._start_capture("keyboard", "undo_only")

    assert screen._draft.has_conflicts is True
    assert screen._draft.sequence("delete_branch") == "Ctrl+Z"
    assert manager.sequence("delete_branch") == "Del"
    assert "Conflicts with:" in (
        screen._keyboard_conflict_labels["delete_branch"].text()
    )
    assert screen._capture_kind == "keyboard"

    localization.set_locale("ru-RU", persist=False)

    assert screen._header.title_label.text() == "Назначения клавиш и мыши"
    assert screen._keyboard_cards["delete_branch"].title_label.text() == (
        "Удалить выбранную ветку"
    )
    assert screen._mouse_chips["move_node"].text() == "Правая кнопка"
    assert screen._draft.has_conflicts is True
    assert screen._draft.sequence("delete_branch") == "Ctrl+Z"
    assert manager.sequence("delete_branch") == "Del"
    assert "Конфликт с:" in (
        screen._keyboard_conflict_labels["delete_branch"].text()
    )
    assert screen._capture_kind == "keyboard"
    assert screen._capture_binding_id == "undo_only"
    assert screen._sequence_chips["undo_only"]._capturing is True

    localization.set_locale("en-US", persist=False)

    assert screen._draft.sequence("delete_branch") == "Ctrl+Z"
    assert "Conflicts with:" in (
        screen._keyboard_conflict_labels["delete_branch"].text()
    )

    screen._cancel_capture()
    screen.deleteLater()
    app.processEvents()


def test_keybinding_dialogs_switch_language_without_losing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    localization = _localization(app, monkeypatch)

    shortcut = _ShortcutCaptureDialog(
        "keybindings.binding.history_toggle.title",
        "Ctrl+Y",
        localization,
    )
    mouse = _MouseGestureDialog(
        "keybindings.mouse_binding.pan_canvas_secondary.title",
        "middle",
        "alt",
        wheel_only=False,
        localization=localization,
    )

    assert shortcut.windowTitle() == "Edit shortcut"
    assert shortcut._heading.text() == "Undo or restore the latest change"
    assert shortcut.sequence() == "Ctrl+Y"
    assert mouse.windowTitle() == "Edit mouse gesture"
    assert mouse._button_label.text() == "Mouse button"
    assert mouse._button_box.currentData() == "middle"
    assert mouse._button_box.currentText() == "Middle button"
    assert mouse._modifier_box.currentData() == "alt"

    localization.set_locale("ru-RU", persist=False)

    assert shortcut.windowTitle() == "Изменить сочетание"
    assert shortcut._heading.text() == "Отменить или вернуть последнее изменение"
    assert shortcut.sequence() == "Ctrl+Y"
    assert mouse.windowTitle() == "Изменить жест мыши"
    assert mouse._button_label.text() == "Кнопка мыши"
    assert mouse._button_box.currentData() == "middle"
    assert mouse._button_box.currentText() == "Средняя кнопка"
    assert mouse._modifier_box.currentData() == "alt"

    shortcut.deleteLater()
    mouse.deleteLater()
    app.processEvents()


def test_keybinding_storage_errors_are_semantic_and_render_per_locale(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    localization = _localization(app, monkeypatch)
    path = tmp_path / "key_bindings.json"
    path.write_text("{not-json", encoding="utf-8")

    manager = KeyBindingManager(storage_path=path)
    message = manager.last_error_message

    assert message is not None
    assert message.key == "keybindings.error.read"
    assert render_user_message(localization, message).startswith(
        "Could not read key bindings:"
    )

    localization.set_locale("ru-RU", persist=False)

    assert render_user_message(localization, message).startswith(
        "Не удалось прочитать назначения клавиш:"
    )
