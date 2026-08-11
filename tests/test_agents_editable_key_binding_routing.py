from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.history_binding_ownership import (
    HistoryBindingOwnership,
)
from persona_training_lab.ui.agents.history_gesture_core import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryGestureCore,
)
from persona_training_lab.ui.agents.history_shortcut_routing import (
    HistoryShortcutRouting,
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


def _ownership(
    manager: KeyBindingManager,
) -> tuple[
    HistoryBindingOwnership,
    HistoryGestureCore,
    dict[str, _FakeShortcut],
]:
    routing = HistoryShortcutRouting()
    core = HistoryGestureCore()
    shortcuts = {
        binding_id: _FakeShortcut()
        for binding_id in routing.binding_ids
    }
    return (
        HistoryBindingOwnership(
            routing=routing,
            gesture=core,
            shortcuts=shortcuts,
        ),
        core,
        shortcuts,
    )


def _sequences(manager: KeyBindingManager) -> dict[str, str]:
    return {
        binding_id: manager.sequence(binding_id)
        for binding_id in HistoryShortcutRouting.binding_ids
    }


def test_default_history_bindings_use_physical_guard(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    ownership, core, shortcuts = _ownership(manager)

    guarded = ownership.sync(_sequences(manager))

    assert guarded == {"history_toggle", "undo_only"}
    assert core.guarded_bindings == {"history_toggle", "undo_only"}
    assert shortcuts["history_toggle"].enabled is False
    assert shortcuts["undo_only"].enabled is False


def test_custom_history_binding_switches_to_qshortcut_live(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    ownership, core, shortcuts = _ownership(manager)
    assert manager.set_sequence("history_toggle", "Ctrl+Y").accepted

    guarded = ownership.sync(_sequences(manager))

    assert guarded == {"undo_only"}
    assert core.guarded_bindings == {"undo_only"}
    assert shortcuts["history_toggle"].enabled is True
    assert shortcuts["undo_only"].enabled is False
    assert core.allowed_actions((HISTORY_TOGGLE, HISTORY_UNDO)) == (
        HISTORY_UNDO,
    )


def test_custom_alt_z_is_not_swallowed_by_default_ctrl_z_guard() -> None:
    modifiers = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Z, modifiers, "\x1a")
    core = HistoryGestureCore()
    core.set_guarded_bindings(("history_toggle",))

    def unexpected_observation(_event: QKeyEvent) -> tuple[bool, bool]:
        raise AssertionError("extra-modifier Z must bypass modifier observation")

    screen = SimpleNamespace(
        _history_gesture=core,
        _has_extra_history_modifiers=(
            HistoryKeyGuardAgentsScreen._has_extra_history_modifiers
        ),
        _observed_modifiers=unexpected_observation,
        _apply_history_gesture_transition=lambda _transition: None,
    )

    assert HistoryKeyGuardAgentsScreen._claims_history_override(
        screen,
        event,
        "z",
    ) is False
    assert HistoryKeyGuardAgentsScreen._handle_history_key_press(
        screen,
        event,
        "z",
    ) is False
    assert core.z_down is False
    assert core.control_down is False


def test_unowned_history_transport_never_observes_or_mutates_key_state() -> None:
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Z,
        Qt.KeyboardModifier.ControlModifier,
        "\x1a",
    )
    core = HistoryGestureCore()

    def unexpected_observation(_event: QKeyEvent) -> tuple[bool, bool]:
        raise AssertionError("unowned history transport must stay completely inert")

    screen = SimpleNamespace(
        _history_gesture=core,
        _has_extra_history_modifiers=(
            HistoryKeyGuardAgentsScreen._has_extra_history_modifiers
        ),
        _observed_modifiers=unexpected_observation,
        _apply_history_gesture_transition=lambda _transition: None,
    )

    assert HistoryKeyGuardAgentsScreen._claims_history_override(
        screen,
        event,
        "z",
    ) is False
    assert HistoryKeyGuardAgentsScreen._handle_history_key_press(
        screen,
        event,
        "z",
    ) is False
    assert core.control_down is False
    assert core.z_down is False
    assert core.mode is None


def test_reset_to_default_restores_physical_guard(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    ownership, core, shortcuts = _ownership(manager)
    assert manager.set_sequence("undo_only", "Ctrl+Alt+Z").accepted
    ownership.sync(_sequences(manager))
    assert shortcuts["undo_only"].enabled is True

    assert manager.reset_binding("undo_only").accepted
    ownership.sync(_sequences(manager))

    assert "undo_only" in core.guarded_bindings
    assert shortcuts["undo_only"].enabled is False
