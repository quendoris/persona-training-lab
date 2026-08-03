from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent

from persona_training_lab.ui.agents import AgentsScreen as PublicAgentsScreen
from persona_training_lab.ui.agents.screen_agents_final import AgentsScreen as FinalAgentsScreen


def test_public_agents_screen_uses_final_bounded_layout() -> None:
    assert PublicAgentsScreen is FinalAgentsScreen
    assert FinalAgentsScreen._ROLES_MIN_WIDTH >= 280
    assert FinalAgentsScreen._DETAILS_MIN_WIDTH >= 360


def test_history_debug_log_has_stable_local_path() -> None:
    path = FinalAgentsScreen._history_debug_path()

    assert isinstance(path, Path)
    assert path.name == "history_input_debug.log"
    assert path.parent.name == ".persona_training_lab"


def test_internal_window_deactivation_is_not_an_application_history_reset() -> None:
    assert FinalAgentsScreen._INTERNAL_WINDOW_DEACTIVATION == QEvent.Type.WindowDeactivate
