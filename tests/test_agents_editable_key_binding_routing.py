from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.history_gesture_core import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryGestureCore,
)
from persona_training_lab.ui.agents.screen_history_keyguard import (
    AgentsScreen as HistoryKeyGuardAgentsScreen,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager


class _FakeShortcut:
    def __init__(self) -> None:
        self.enabled: bool | None = None

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        self.enabled = enabled


def _routing_screen(manager: KeyBindingManager):
    shortcuts = {
        "history_toggle": _FakeShortcut(),
        "undo_only": _FakeShortcut(),
    }
    screen = SimpleNamespace(
        _key_binding_manager=manager,
        _shortcuts=shortcuts,
        _HISTORY_BINDING_IDS=HistoryKeyGuardAgentsScreen._HISTORY_BINDING_IDS,
        _DEFAULT_GUARDED_SEQUENCES=HistoryKeyGuardAgentsScreen._DEFAULT_GUARDED_SEQUENCES,
        _normalized_sequence=HistoryKeyGuardAgentsScreen._normalized_sequence,
        _history_gesture=HistoryGestureCore(),
        _sync_modifier_polling=lambda: None,
    )
    return screen, shortcuts


def test_default_history_bindings_use_physical_guard(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    screen, shortcuts = _routing_screen(manager)

    HistoryKeyGuardAgentsScreen._sync_history_shortcut_routing(screen)

    assert screen._history_gesture.guarded_bindings == {"history_toggle", "undo_only"}
    assert shortcuts["history_toggle"].enabled is False
    assert shortcuts["undo_only"].enabled is False


def test_custom_history_binding_switches_to_qshortcut_live(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    screen, shortcuts = _routing_screen(manager)
    assert manager.set_sequence("history_toggle", "Ctrl+Y").accepted

    HistoryKeyGuardAgentsScreen._sync_history_shortcut_routing(screen)

    assert screen._history_gesture.guarded_bindings == {"undo_only"}
    assert shortcuts["history_toggle"].enabled is True
    assert shortcuts["undo_only"].enabled is False
    assert HistoryKeyGuardAgentsScreen._guarded_actions(screen, (HISTORY_TOGGLE, HISTORY_UNDO)) == (
        HISTORY_UNDO,
    )


def test_custom_alt_z_is_not_swallowed_by_default_ctrl_z_guard() -> None:
    modifiers = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Z, modifiers, "\x1a")
    core = HistoryGestureCore()
    core.set_guarded_bindings(("history_toggle",))
    screen = SimpleNamespace(
        _history_gesture=core,
        _has_extra_history_modifiers=HistoryKeyGuardAgentsScreen._has_extra_history_modifiers,
        _effective_modifiers=lambda _event: (True, False),
        _apply_history_transition=lambda _transition: None,
    )

    assert HistoryKeyGuardAgentsScreen._claims_history_override(screen, event, "z") is False
    assert HistoryKeyGuardAgentsScreen._handle_history_key_press(screen, event, "z") is False
    assert core.z_down is False


def test_reset_to_default_restores_physical_guard(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    screen, shortcuts = _routing_screen(manager)
    assert manager.set_sequence("undo_only", "Ctrl+Alt+Z").accepted
    HistoryKeyGuardAgentsScreen._sync_history_shortcut_routing(screen)
    assert shortcuts["undo_only"].enabled is True

    assert manager.reset_binding("undo_only").accepted
    HistoryKeyGuardAgentsScreen._sync_history_shortcut_routing(screen)

    assert "undo_only" in screen._history_gesture.guarded_bindings
    assert shortcuts["undo_only"].enabled is False
