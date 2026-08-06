from __future__ import annotations

from PySide6.QtGui import QKeySequence

from persona_training_lab.ui.agents.history_key_state import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryKeyState,
)
from persona_training_lab.ui.agents.history_shortcut_routing import (
    HistoryShortcutRouting,
)


def test_default_history_sequences_are_guarded_but_custom_ones_are_not() -> None:
    routing = HistoryShortcutRouting()

    guarded = routing.guarded_bindings(
        {
            "history_toggle": "Ctrl + Z",
            "undo_only": "Alt+Backspace",
        }
    )

    assert guarded == frozenset({"history_toggle"})


def test_allowed_actions_preserve_order_and_drop_unowned_history_actions() -> None:
    routing = HistoryShortcutRouting()

    assert routing.allowed_actions(
        (HISTORY_TOGGLE, HISTORY_UNDO, HISTORY_TOGGLE),
        {"undo_only"},
    ) == (HISTORY_UNDO,)


def test_guarded_gesture_switches_from_toggle_to_strict_undo() -> None:
    routing = HistoryShortcutRouting()
    state = HistoryKeyState()
    state.press("control")
    state.press("z")

    assert routing.gesture_is_guarded(state, {"history_toggle"}) is True
    assert routing.gesture_is_guarded(state, {"undo_only"}) is False

    state.press("shift")

    assert routing.gesture_is_guarded(state, {"history_toggle"}) is False
    assert routing.gesture_is_guarded(state, {"undo_only"}) is True


def test_override_claim_uses_current_chord_and_configured_owner() -> None:
    routing = HistoryShortcutRouting()
    state = HistoryKeyState()

    assert routing.claims_override(
        key_name="z",
        control=True,
        shift=False,
        has_extra_modifiers=False,
        state=state,
        guarded_bindings={"history_toggle"},
    ) is True
    assert routing.claims_override(
        key_name="z",
        control=True,
        shift=True,
        has_extra_modifiers=False,
        state=state,
        guarded_bindings={"history_toggle"},
    ) is False
    assert routing.claims_override(
        key_name="z",
        control=True,
        shift=True,
        has_extra_modifiers=False,
        state=state,
        guarded_bindings={"undo_only"},
    ) is True


def test_extra_modifiers_never_claim_history_override() -> None:
    routing = HistoryShortcutRouting()

    assert routing.claims_override(
        key_name="z",
        control=True,
        shift=False,
        has_extra_modifiers=True,
        state=HistoryKeyState(),
        guarded_bindings={"history_toggle"},
    ) is False


def test_history_sequence_recognition_uses_portable_normalization() -> None:
    routing = HistoryShortcutRouting()

    assert routing.sequence_is_history(QKeySequence("Ctrl + Z")) is True
    assert routing.sequence_is_history(QKeySequence("Ctrl+Shift+Z")) is True
    assert routing.sequence_is_history(QKeySequence("Delete")) is False
