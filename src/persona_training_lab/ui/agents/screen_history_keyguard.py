from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.agents.key_bindings import agent_graph_key_bindings_by_id
from persona_training_lab.ui.agents.screen_stateful_fixed import AgentsScreen as _StatefulFixedAgentsScreen


class AgentsScreen(_StatefulFixedAgentsScreen):
    """Own history key events before Qt can route them to another action."""

    _HISTORY_BINDING_IDS = ("history_toggle", "undo_only")

    def __init__(self, view_model) -> None:
        super().__init__(view_model)

        # QShortcut can become ambiguous when Ctrl+Z and Ctrl+Shift+Z coexist
        # with auto-repeat and Qt's platform-standard Undo/Redo mappings. Disable
        # those two shortcuts and consume their raw key events instead.
        for binding_id in self._HISTORY_BINDING_IDS:
            shortcut = getattr(self, "_shortcuts", {}).get(binding_id)
            if shortcut is not None:
                shortcut.setEnabled(False)

        definitions = agent_graph_key_bindings_by_id()
        self._history_key_combinations: dict[int, str] = {}
        for binding_id in self._HISTORY_BINDING_IDS:
            sequence = QKeySequence.fromString(
                definitions[binding_id].sequence,
                QKeySequence.SequenceFormat.PortableText,
            )
            if sequence.count() == 1:
                self._history_key_combinations[int(sequence[0].toCombined())] = binding_id

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if event.type() not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            return super().eventFilter(watched, event)
        if not isinstance(event, QKeyEvent) or not self._history_keys_are_active():
            return super().eventFilter(watched, event)

        binding_id = self._history_key_combinations.get(int(event.keyCombination().toCombined()))
        if binding_id is None:
            return super().eventFilter(watched, event)

        # Consume both press and release so the sequence cannot leak to a focused
        # button, a standard Redo action, or another shortcut after auto-repeat.
        if event.type() == QEvent.Type.KeyPress:
            if binding_id == "history_toggle":
                # Ctrl+Z toggles once per physical press; holding it must not
                # oscillate rapidly between undo and redo.
                if not event.isAutoRepeat():
                    self._toggle_last_history_action()
            elif binding_id == "undo_only":
                # Ctrl+Shift+Z intentionally supports auto-repeat for walking
                # backwards through the history.
                self._undo_history_only()
        event.accept()
        return True

    def _history_keys_are_active(self) -> bool:
        app = QApplication.instance()
        if app is None or not self.isVisible() or not self.window().isActiveWindow():
            return False
        if app.activeModalWidget() is not None:
            return False
        focus = app.focusWidget()
        return focus is None or focus.window() is self.window()
