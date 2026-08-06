from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from PySide6.QtGui import QKeySequence

from persona_training_lab.ui.agents.history_key_state import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryKeyState,
)


@dataclass(frozen=True, slots=True)
class HistoryShortcutRouting:
    """Choose which history gestures bypass ordinary Qt shortcut routing."""

    binding_ids = ("history_toggle", "undo_only")
    default_sequences = {
        "history_toggle": "Ctrl+Z",
        "undo_only": "Ctrl+Shift+Z",
    }
    history_sequences = frozenset({"ctrl+z", "ctrl+shift+z"})

    def guarded_bindings(
        self,
        sequences: Mapping[str, str],
    ) -> frozenset[str]:
        return frozenset(
            binding_id
            for binding_id, default_sequence in self.default_sequences.items()
            if self.normalized_sequence(sequences.get(binding_id, ""))
            == self.normalized_sequence(default_sequence)
        )

    @staticmethod
    def allowed_actions(
        actions: Iterable[str],
        guarded_bindings: set[str] | frozenset[str],
    ) -> tuple[str, ...]:
        allowed: list[str] = []
        for action in actions:
            if (
                action == HISTORY_TOGGLE
                and "history_toggle" in guarded_bindings
            ):
                allowed.append(action)
            elif action == HISTORY_UNDO and "undo_only" in guarded_bindings:
                allowed.append(action)
        return tuple(allowed)

    @staticmethod
    def gesture_is_guarded(
        state: HistoryKeyState,
        guarded_bindings: set[str] | frozenset[str],
    ) -> bool:
        if not state.history_gesture_active:
            return False
        if state.strict_undo_requested:
            return "undo_only" in guarded_bindings
        return "history_toggle" in guarded_bindings

    def claims_override(
        self,
        *,
        key_name: str | None,
        control: bool,
        shift: bool,
        has_extra_modifiers: bool,
        state: HistoryKeyState,
        guarded_bindings: set[str] | frozenset[str],
    ) -> bool:
        if key_name is None or not guarded_bindings:
            return False
        if key_name == "z" and has_extra_modifiers:
            return False
        if key_name == "z" and control:
            binding_id = "undo_only" if shift else "history_toggle"
            return binding_id in guarded_bindings
        if key_name == "shift" and state.control_down and state.z_down:
            return "undo_only" in guarded_bindings
        if key_name == "control" and state.z_down:
            return self.gesture_is_guarded(state, guarded_bindings)
        return state.mode is not None and key_name in {
            "control",
            "shift",
            "z",
        }

    @staticmethod
    def normalized_sequence(sequence: str) -> str:
        parsed = QKeySequence.fromString(
            sequence,
            QKeySequence.SequenceFormat.PortableText,
        )
        return (
            parsed.toString(QKeySequence.SequenceFormat.PortableText)
            .replace(" ", "")
            .casefold()
        )

    def sequence_is_history(self, sequence: QKeySequence) -> bool:
        text = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        return text.replace(" ", "").casefold() in self.history_sequences
