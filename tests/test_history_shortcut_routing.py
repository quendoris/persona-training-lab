from __future__ import annotations

import pytest
from PySide6.QtGui import QKeySequence

from persona_training_lab.ui.agents.history_shortcut_routing import HistoryShortcutRouting


def test_default_history_sequences_are_guarded_but_custom_ones_are_not() -> None:
    routing = HistoryShortcutRouting()

    guarded = routing.guarded_bindings(
        {
            "history_toggle": "Ctrl + Z",
            "undo_only": "Alt+Backspace",
        }
    )

    assert guarded == frozenset({"history_toggle"})


def test_routing_defaults_are_immutable_global_contract() -> None:
    routing = HistoryShortcutRouting()

    with pytest.raises(TypeError):
        routing.default_sequences["history_toggle"] = "Alt+Z"  # type: ignore[index]

    assert routing.default_sequences["history_toggle"] == "Ctrl+Z"


def test_history_sequence_recognition_uses_portable_normalization() -> None:
    routing = HistoryShortcutRouting()

    assert routing.sequence_is_history(QKeySequence("Ctrl + Z")) is True
    assert routing.sequence_is_history(QKeySequence("Ctrl+Shift+Z")) is True
    assert routing.sequence_is_history(QKeySequence("Delete")) is False
