from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtGui import QKeySequence

from persona_training_lab.ui.keybindings.manager import KeyBindingManager


class ShortcutBindingPort(Protocol):
    def setKey(self, key: QKeySequence) -> None:  # noqa: N802
        ...

    def setAutoRepeat(self, enabled: bool) -> None:  # noqa: N802
        ...


@dataclass(slots=True)
class ShortcutBindingSynchronizer:
    """Apply one manager snapshot to ordinary Qt shortcut transports."""

    manager: KeyBindingManager
    shortcuts: Mapping[str, ShortcutBindingPort]

    def sync(self) -> dict[str, str]:
        definitions = {
            item.binding_id: item
            for item in self.manager.definitions()
        }
        sequences: dict[str, str] = {}

        for binding_id, shortcut in self.shortcuts.items():
            sequence_text = self.manager.sequence(binding_id)
            sequences[binding_id] = sequence_text
            shortcut.setKey(
                QKeySequence.fromString(
                    sequence_text,
                    QKeySequence.SequenceFormat.PortableText,
                )
            )
            definition = definitions.get(binding_id)
            if definition is not None:
                shortcut.setAutoRepeat(definition.auto_repeat)

        return sequences
