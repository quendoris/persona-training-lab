from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar

from PySide6.QtGui import QKeySequence


@dataclass(frozen=True, slots=True)
class HistoryShortcutRouting:
    """Resolve which history bindings must bypass ordinary Qt shortcut routing."""

    binding_ids: ClassVar[tuple[str, str]] = (
        "history_toggle",
        "undo_only",
    )
    default_sequences: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "history_toggle": "Ctrl+Z",
            "undo_only": "Ctrl+Shift+Z",
        }
    )
    history_sequences: ClassVar[frozenset[str]] = frozenset(
        {"ctrl+z", "ctrl+shift+z"}
    )

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
