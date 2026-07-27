from __future__ import annotations

from persona_training_lab.ui.agents.history_key_state import HISTORY_TOGGLE, HISTORY_UNDO, HistoryKeyState


def test_ctrl_z_then_shift_switches_live_gesture_to_undo_only() -> None:
    state = HistoryKeyState()

    assert state.press("control") == ()
    assert state.press("z") == (HISTORY_TOGGLE,)
    assert state.press("shift") == (HISTORY_UNDO,)
    assert state.undo_repeat_active is True


def test_ctrl_shift_z_starts_with_undo_without_toggle() -> None:
    state = HistoryKeyState()

    assert state.press("control") == ()
    assert state.press("shift") == ()
    assert state.press("z") == (HISTORY_UNDO,)
    assert state.undo_repeat_active is True


def test_repeated_keypresses_do_not_duplicate_history_actions() -> None:
    state = HistoryKeyState()
    state.press("control")
    assert state.press("z") == (HISTORY_TOGGLE,)

    assert state.press("z") == ()
    assert state.press("control") == ()


def test_releasing_shift_keeps_same_z_gesture_in_strict_undo_mode() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.press("z")
    state.press("shift")

    assert state.release("shift") is True
    assert state.undo_repeat_active is True
    assert state.press("z") == ()
    assert state.mode == "undo_only"

    assert state.release("z") is True
    assert state.mode is None
    assert state.shift_latched is False
    assert state.press("z") == (HISTORY_TOGGLE,)


def test_system_layout_switch_shift_release_before_z_still_means_undo() -> None:
    state = HistoryKeyState()

    assert state.press("control") == ()
    assert state.press("shift") == ()
    assert state.shift_latched is True

    # Linux Ctrl+Shift layout switching may report Shift release before the next
    # application key event even while the user's physical chord continues.
    assert state.release("shift") is False
    assert state.shift_down is False
    assert state.shift_latched is True

    assert state.press("z") == (HISTORY_UNDO,)
    assert state.undo_repeat_active is True


def test_modifiers_can_be_primed_when_z_event_arrives_first() -> None:
    state = HistoryKeyState()
    state.prime_modifiers(control=True, shift=True)

    assert state.press("z") == (HISTORY_UNDO,)
