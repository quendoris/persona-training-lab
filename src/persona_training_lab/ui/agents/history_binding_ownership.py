from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from persona_training_lab.ui.agents.history_gesture_core import HistoryGestureCore
from persona_training_lab.ui.agents.history_shortcut_routing import (
    HistoryShortcutRouting,
)


class HistoryShortcutPort(Protocol):
    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        ...


@dataclass(slots=True)
class HistoryBindingOwnership:
    """Synchronize physical history ownership with ordinary shortcut routing."""

    routing: HistoryShortcutRouting
    gesture: HistoryGestureCore
    shortcuts: Mapping[str, HistoryShortcutPort]

    def sync(self, sequences: Mapping[str, str]) -> frozenset[str]:
        guarded = self.routing.guarded_bindings(sequences)
        self.gesture.set_guarded_bindings(guarded)

        for binding_id in self.routing.binding_ids:
            shortcut = self.shortcuts.get(binding_id)
            if shortcut is not None:
                shortcut.setEnabled(binding_id not in guarded)

        return guarded
