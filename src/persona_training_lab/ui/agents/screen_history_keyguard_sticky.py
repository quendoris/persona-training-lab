from __future__ import annotations

from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen as _HistoryKeyGuardAgentsScreen


class AgentsScreen(_HistoryKeyGuardAgentsScreen):
    """Keep observed modifiers latched until real key-release events arrive."""

    def _poll_physical_modifiers(self) -> None:
        if not self._history_keys_are_active():
            return

        control, shift = self._queried_modifiers()
        actions: list[str] = []

        # Polling is only a positive fallback for events consumed by the desktop.
        # queryKeyboardModifiers() may briefly report False while Ctrl+Shift changes
        # the XKB layout, so it must never be allowed to release an observed key.
        if control and not self._history_keys.control_down:
            actions.extend(self._history_keys.press("control"))
        if shift:
            actions.extend(self._history_keys.set_physical_shift(True))

        if actions:
            self._block_graph_flip()
            self._dispatch_history_actions(actions)
