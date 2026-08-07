from __future__ import annotations

from PySide6.QtCore import Qt

from persona_training_lab.ui.agents.history_modifier_snapshot import HistoryModifierSnapshot


def test_empty_qt_modifiers_produce_empty_snapshot() -> None:
    snapshot = HistoryModifierSnapshot.from_qt(Qt.KeyboardModifier.NoModifier)

    assert snapshot == HistoryModifierSnapshot()
    assert not snapshot.has_extra_history_modifiers


def test_control_and_shift_are_normalized_independently() -> None:
    snapshot = HistoryModifierSnapshot.from_qt(
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
    )

    assert snapshot.control
    assert snapshot.shift
    assert not snapshot.alt
    assert not snapshot.meta
    assert not snapshot.has_extra_history_modifiers


def test_alt_is_an_extra_history_modifier() -> None:
    snapshot = HistoryModifierSnapshot.from_qt(Qt.KeyboardModifier.AltModifier)

    assert snapshot.alt
    assert snapshot.has_extra_history_modifiers


def test_meta_is_an_extra_history_modifier() -> None:
    snapshot = HistoryModifierSnapshot.from_qt(Qt.KeyboardModifier.MetaModifier)

    assert snapshot.meta
    assert snapshot.has_extra_history_modifiers


def test_combined_qt_mask_preserves_all_history_relevant_modifiers() -> None:
    snapshot = HistoryModifierSnapshot.from_qt(
        Qt.KeyboardModifier.ControlModifier
        | Qt.KeyboardModifier.ShiftModifier
        | Qt.KeyboardModifier.AltModifier
        | Qt.KeyboardModifier.MetaModifier
    )

    assert snapshot == HistoryModifierSnapshot(
        control=True,
        shift=True,
        alt=True,
        meta=True,
    )
