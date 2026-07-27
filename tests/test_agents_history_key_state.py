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


def test_releasing_z_does_not_clear_shift_for_next_strict_undo() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.press("shift")

    assert state.press("z") == (HISTORY_UNDO,)
    assert state.release("z") is True
    assert state.mode is None
    assert state.strict_undo_requested is True

    assert state.press("z") == (HISTORY_UNDO,)
    assert state.undo_repeat_active is True


def test_physical_shift_flag_clears_only_when_shift_is_really_released() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.set_physical_shift(True)

    assert state.strict_undo_requested is True
    assert state.set_physical_shift(False) == ()
    assert state.strict_undo_requested is False
    assert state.press("z") == (HISTORY_TOGGLE,)


def test_layout_change_latch_survives_consumed_shift_event_until_control_release() -> None:
    state = HistoryKeyState()
    state.press("control")

    assert state.latch_layout_shift() == ()
    assert state.layout_shift_latched is True
    assert state.set_physical_shift(False) == ()
    assert state.strict_undo_requested is True
    assert state.press("z") == (HISTORY_UNDO,)

    state.release("z")
    state.release("control")
    assert state.layout_shift_latched is False
    assert state.strict_undo_requested is False


def test_layout_change_while_ctrl_z_is_held_switches_toggle_to_undo() -> None:
    state = HistoryKeyState()
    state.press("control")
    assert state.press("z") == (HISTORY_TOGGLE,)

    assert state.latch_layout_shift() == (HISTORY_UNDO,)
    assert state.mode == "undo_only"


def test_modifiers_can_be_primed_when_z_event_arrives_first() -> None:
    state = HistoryKeyState()
    assert state.prime_modifiers(control=True, shift=True) == ()

    assert state.press("z") == (HISTORY_UNDO,)
