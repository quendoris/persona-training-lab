from __future__ import annotations

import importlib
from types import SimpleNamespace

from persona_training_lab.ui.agents import AgentsScreen as PublicAgentsScreen
from persona_training_lab.ui.agents.history_key_state import HISTORY_TOGGLE, HISTORY_UNDO, HistoryKeyState
from persona_training_lab.ui.agents.screen_agents_final import AgentsScreen as FinalAgentsScreen
from persona_training_lab.ui.agents.screen_history_keyguard import (
    AgentsScreen as HistoryKeyGuardAgentsScreen,
)
from persona_training_lab.ui.agents.screen_history_keyguard_sticky import (
    AgentsScreen as StickyHistoryAgentsScreen,
)


def test_public_agents_screen_uses_final_bounded_layout() -> None:
    assert PublicAgentsScreen is FinalAgentsScreen
    assert FinalAgentsScreen.__bases__ == (HistoryKeyGuardAgentsScreen,)
    assert StickyHistoryAgentsScreen is HistoryKeyGuardAgentsScreen
    assert FinalAgentsScreen._ROLES_MIN_WIDTH >= 280
    assert FinalAgentsScreen._DETAILS_MIN_WIDTH >= 360


def test_final_screen_owns_layout_without_interaction_overrides() -> None:
    assert "eventFilter" not in FinalAgentsScreen.__dict__
    assert "_handle_history_key_release" not in FinalAgentsScreen.__dict__
    assert "_poll_physical_modifiers" not in FinalAgentsScreen.__dict__
    assert "_reset_history_gesture" not in FinalAgentsScreen.__dict__


def test_legacy_diagnostics_import_is_clean_final_screen_alias() -> None:
    legacy_module = importlib.import_module("persona_training_lab.ui.agents.screen_history_diagnostics")

    assert legacy_module.AgentsScreen is FinalAgentsScreen


def test_history_keyguard_accepts_physical_shift_release_before_next_ctrl_z() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.press("shift")
    assert state.press("z") == (HISTORY_UNDO,)
    state.release("z")

    calls = {"stop": 0, "block": 0}
    screen = SimpleNamespace(
        _history_keys=state,
        _stop_undo_repeat=lambda: calls.__setitem__("stop", calls["stop"] + 1),
        _block_graph_flip=lambda: calls.__setitem__("block", calls["block"] + 1),
    )

    assert HistoryKeyGuardAgentsScreen._handle_history_key_release(screen, "shift") is True
    assert state.strict_undo_requested is False
    assert calls == {"stop": 1, "block": 1}
    assert state.press("z") == (HISTORY_TOGGLE,)
