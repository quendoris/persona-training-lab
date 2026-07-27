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


def test_releasing_shift_does_not_turn_same_z_hold_back_into_toggle() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.press("z")
    state.press("shift")

    assert state.release("shift") is True
    assert state.undo_repeat_active is False
    assert state.press("z") == ()
    assert state.mode == "spent"

    assert state.release("z") is True
    assert state.mode is None
    assert state.press("z") == (HISTORY_TOGGLE,)


def test_modifiers_can_be_primed_when_z_event_arrives_first() -> None:
    state = HistoryKeyState()
    state.prime_modifiers(control=True, shift=True)

    assert state.press("z") == (HISTORY_UNDO,)
