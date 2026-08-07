from __future__ import annotations

from persona_training_lab.ui.agents.history_gesture_core import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryGestureCore,
)


class _Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _core(*bindings: str, clock=None) -> HistoryGestureCore:
    core = HistoryGestureCore(clock=clock or _Clock())
    core.set_guarded_bindings(bindings)
    return core


def _press(
    core: HistoryGestureCore,
    key_name: str,
    *,
    control: bool = False,
    shift: bool = False,
    extra: bool = False,
    auto_repeat: bool = False,
):
    return core.press(
        key_name,
        observed_control=control,
        observed_shift=shift,
        has_extra_modifiers=extra,
        auto_repeat=auto_repeat,
    )


def test_ctrl_z_then_shift_switches_live_gesture_to_undo_only() -> None:
    core = _core("history_toggle", "undo_only")

    assert _press(core, "control").actions == ()
    assert _press(core, "z").actions == (HISTORY_TOGGLE,)
    assert _press(core, "shift").actions == (HISTORY_UNDO,)
    assert core.undo_repeat_active is True


def test_ctrl_shift_z_starts_with_undo_without_toggle() -> None:
    core = _core("history_toggle", "undo_only")

    _press(core, "control")
    _press(core, "shift")

    result = _press(core, "z")

    assert result.claimed is True
    assert result.actions == (HISTORY_UNDO,)
    assert core.undo_repeat_active is True


def test_repeated_keypresses_are_claimed_without_duplicate_actions() -> None:
    core = _core("history_toggle")
    _press(core, "control")
    assert _press(core, "z").actions == (HISTORY_TOGGLE,)

    repeated = _press(core, "z", auto_repeat=True)

    assert repeated.claimed is True
    assert repeated.actions == ()


def test_releasing_z_preserves_shift_for_next_strict_undo() -> None:
    core = _core("undo_only")
    _press(core, "control")
    _press(core, "shift")
    _press(core, "z")

    released = core.release("z")

    assert released.claimed is True
    assert released.stop_repeat is True
    assert core.mode is None
    assert core.strict_undo_requested is True
    assert _press(core, "z").actions == (HISTORY_UNDO,)


def test_physical_shift_release_restores_toggle_after_strict_undo() -> None:
    core = _core("history_toggle", "undo_only")
    _press(core, "control")
    _press(core, "shift")
    _press(core, "z")
    core.release("z")

    released = core.release("shift")

    assert released.stop_repeat is True
    assert core.control_down is True
    assert core.shift_down is False
    assert core.shift_latched is False
    assert core.strict_undo_requested is False
    assert _press(core, "z").actions == (HISTORY_TOGGLE,)


def test_shift_release_does_not_retoggle_current_strict_chord() -> None:
    core = _core("history_toggle", "undo_only")
    _press(core, "control")
    _press(core, "shift")
    assert _press(core, "z").actions == (HISTORY_UNDO,)

    released = core.release("shift")

    assert released.claimed is True
    assert core.mode == "spent"
    assert core.strict_undo_requested is False
    assert _press(core, "z").actions == ()


def test_layout_change_latch_survives_until_control_release() -> None:
    core = _core("undo_only")
    _press(core, "control")

    changed = core.layout_changed(observed_control=True)

    assert changed.actions == ()
    assert core.layout_shift_latched is True
    assert core.shift_down is False
    assert _press(core, "z").actions == (HISTORY_UNDO,)
    assert core.shift_down is False

    core.release("z")
    core.release("control")

    assert core.layout_shift_latched is False
    assert core.strict_undo_requested is False


def test_layout_change_while_ctrl_z_is_held_switches_toggle_to_undo() -> None:
    core = _core("history_toggle", "undo_only")
    _press(core, "control")
    assert _press(core, "z").actions == (HISTORY_TOGGLE,)

    changed = core.layout_changed(observed_control=True)

    assert changed.actions == (HISTORY_UNDO,)
    assert core.mode == "undo_only"


def test_layout_change_is_ignored_when_undo_binding_is_not_owned() -> None:
    core = _core("history_toggle")
    _press(core, "control")

    changed = core.layout_changed(observed_control=True)

    assert changed.actions == ()
    assert core.layout_shift_latched is False


def test_modifiers_are_primed_when_z_event_arrives_first() -> None:
    core = _core("undo_only")

    result = _press(core, "z", control=True, shift=True)

    assert result.claimed is True
    assert result.actions == (HISTORY_UNDO,)
    assert core.undo_repeat_active is True


def test_extra_modifier_z_is_neither_claimed_nor_mutated() -> None:
    core = _core("history_toggle")

    result = _press(core, "z", control=True, extra=True)

    assert result.claimed is False
    assert result.actions == ()
    assert core.z_down is False
    assert core.control_down is False


def test_guarded_ownership_filters_actions_without_reordering() -> None:
    core = _core("undo_only")

    assert core.allowed_actions((HISTORY_TOGGLE, HISTORY_UNDO, HISTORY_TOGGLE)) == (
        HISTORY_UNDO,
    )


def test_gesture_guard_tracks_toggle_and_strict_ownership() -> None:
    core = _core("history_toggle")
    _press(core, "control")
    _press(core, "z")

    assert core.gesture_is_guarded() is True

    core.set_guarded_bindings(("undo_only",))
    assert core.gesture_is_guarded() is False

    _press(core, "shift")
    assert core.gesture_is_guarded() is True


def test_override_claim_uses_current_chord_and_binding_owner() -> None:
    core = _core("history_toggle")

    assert core.claims_override(
        key_name="z",
        observed_control=True,
        observed_shift=False,
        has_extra_modifiers=False,
    )
    assert not core.claims_override(
        key_name="z",
        observed_control=True,
        observed_shift=True,
        has_extra_modifiers=False,
    )

    core.set_guarded_bindings(("undo_only",))
    assert core.claims_override(
        key_name="z",
        observed_control=True,
        observed_shift=True,
        has_extra_modifiers=False,
    )


def test_override_never_claims_extra_modifier_z() -> None:
    core = _core("history_toggle")

    assert not core.claims_override(
        key_name="z",
        observed_control=True,
        observed_shift=False,
        has_extra_modifiers=True,
    )


def test_positive_poll_can_promote_held_z_from_toggle_to_strict_undo() -> None:
    core = _core("history_toggle", "undo_only")
    _press(core, "z")

    first = core.poll_modifiers(observed_control=True, observed_shift=False)
    second = core.poll_modifiers(observed_control=True, observed_shift=True)

    assert first.actions == (HISTORY_TOGGLE,)
    assert second.actions == (HISTORY_UNDO,)
    assert core.undo_repeat_active is True


def test_poll_never_releases_observed_modifiers_on_false_snapshot() -> None:
    core = _core("undo_only")
    core.poll_modifiers(observed_control=True, observed_shift=True)

    core.poll_modifiers(observed_control=False, observed_shift=False)

    assert core.control_down is True
    assert core.shift_down is True


def test_repeat_requires_owned_strict_gesture_and_available_undo() -> None:
    core = _core("undo_only")
    _press(core, "control")
    _press(core, "shift")
    _press(core, "z")

    assert core.repeat_is_allowed(can_undo=True) is True
    assert core.repeat_is_allowed(can_undo=False) is False

    core.set_guarded_bindings(())
    assert core.repeat_is_allowed(can_undo=True) is False


def test_flip_guard_deadline_extends_but_never_moves_backwards() -> None:
    clock = _Clock(10.0)
    core = _core(clock=clock)

    assert core.block_flip() == 10.35

    clock.value = 10.1
    assert core.block_flip() == 10.45

    clock.value = 10.05
    assert core.block_flip() == 10.45


def test_flip_guard_combines_state_external_modifiers_and_deadline() -> None:
    clock = _Clock(2.0)
    core = _core("history_toggle", clock=clock)
    core.block_flip()

    clock.value = 2.349
    assert core.flip_is_blocked(modifier_guarded=False) is True

    clock.value = 2.35
    assert core.flip_is_blocked(modifier_guarded=False) is False
    assert core.flip_is_blocked(modifier_guarded=True) is True

    _press(core, "control")
    _press(core, "z")
    clock.value = 10.0
    assert core.flip_is_blocked(modifier_guarded=False) is True


def test_reset_clears_gesture_state_and_refreshes_flip_guard() -> None:
    clock = _Clock(4.0)
    core = _core("undo_only", clock=clock)
    _press(core, "control")
    _press(core, "shift")
    _press(core, "z")

    core.reset()

    assert core.control_down is False
    assert core.shift_down is False
    assert core.z_down is False
    assert core.mode is None
    assert core.strict_undo_requested is False
    assert core.flip_blocked_until == 4.35
