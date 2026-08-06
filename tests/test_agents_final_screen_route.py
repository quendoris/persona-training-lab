from __future__ import annotations

import importlib
from types import SimpleNamespace

from persona_training_lab.ui.agents import AgentsScreen as PublicAgentsScreen
from persona_training_lab.ui.agents.history_key_state import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryKeyState,
)
from persona_training_lab.ui.agents.screen_agents_final import (
    AgentsScreen as FinalAgentsScreen,
)
from persona_training_lab.ui.agents.screen_background import (
    AgentsScreen as BackgroundAgentsScreen,
)
from persona_training_lab.ui.agents.screen_background_fast import (
    AgentsScreen as FastBackgroundAgentsScreen,
)
from persona_training_lab.ui.agents.screen_background_reconciled import (
    AgentsScreen as ReconciledBackgroundAgentsScreen,
)
from persona_training_lab.ui.agents.screen_background_reported import (
    AgentsScreen as ReportedBackgroundAgentsScreen,
)
from persona_training_lab.ui.agents.screen_contextual import (
    AgentsScreen as ContextualAgentsScreen,
)
from persona_training_lab.ui.agents.screen_history_keyguard import (
    AgentsScreen as HistoryKeyGuardAgentsScreen,
)
from persona_training_lab.ui.agents.screen_history_keyguard_sticky import (
    AgentsScreen as StickyHistoryAgentsScreen,
)
from persona_training_lab.ui.agents.screen_runtime_safe import (
    AgentsScreen as RuntimeSafeAgentsScreen,
)


def test_public_agents_screen_uses_single_composed_background_layout() -> None:
    assert PublicAgentsScreen is BackgroundAgentsScreen
    assert ContextualAgentsScreen is BackgroundAgentsScreen
    assert FastBackgroundAgentsScreen is BackgroundAgentsScreen
    assert ReconciledBackgroundAgentsScreen is BackgroundAgentsScreen
    assert ReportedBackgroundAgentsScreen is BackgroundAgentsScreen
    assert RuntimeSafeAgentsScreen is BackgroundAgentsScreen
    assert BackgroundAgentsScreen.__bases__ == (FinalAgentsScreen,)
    assert FinalAgentsScreen.__bases__ == (HistoryKeyGuardAgentsScreen,)
    assert StickyHistoryAgentsScreen is HistoryKeyGuardAgentsScreen
    assert FinalAgentsScreen._ROLES_MIN_WIDTH >= 280
    assert FinalAgentsScreen._DETAILS_MIN_WIDTH >= 360


def test_background_screen_owns_runtime_and_contextual_ui_adapters() -> None:
    for method_name in (
        "_detail_for",
        "_sync_detail_actions",
        "_render_detail",
        "_apply_projection",
        "_show_runtime_blockers",
        "_open_workspace",
        "_on_graph_zoom_anchor",
        "_on_graph_workspace_origin_shift",
        "_delete_local_branch_subtree",
        "_apply_branch_deletion_result",
        "_context_for_node",
    ):
        assert method_name in BackgroundAgentsScreen.__dict__
    assert "eventFilter" not in BackgroundAgentsScreen.__dict__
    assert "_handle_history_key_release" not in BackgroundAgentsScreen.__dict__


def test_final_screen_owns_layout_without_interaction_overrides() -> None:
    assert "eventFilter" not in FinalAgentsScreen.__dict__
    assert "_handle_history_key_release" not in FinalAgentsScreen.__dict__
    assert "_poll_physical_modifiers" not in FinalAgentsScreen.__dict__
    assert "_reset_history_gesture" not in FinalAgentsScreen.__dict__


def test_historical_screen_imports_are_clean_background_aliases() -> None:
    for module_name in (
        "screen",
        "screen_locked_layout",
        "screen_stateful",
        "screen_history_diagnostics",
    ):
        module = importlib.import_module(
            f"persona_training_lab.ui.agents.{module_name}"
        )
        assert module.AgentsScreen is BackgroundAgentsScreen


def test_history_keyguard_accepts_physical_shift_release_before_next_ctrl_z() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.press("shift")
    assert state.press("z") == (HISTORY_UNDO,)
    state.release("z")

    calls = {"stop": 0, "block": 0}
    screen = SimpleNamespace(
        _history_keys=state,
        _stop_undo_repeat=lambda: calls.__setitem__(
            "stop",
            calls["stop"] + 1,
        ),
        _block_graph_flip=lambda: calls.__setitem__(
            "block",
            calls["block"] + 1,
        ),
    )

    assert HistoryKeyGuardAgentsScreen._handle_history_key_release(
        screen,
        "shift",
    ) is True
    assert state.strict_undo_requested is False
    assert calls == {"stop": 1, "block": 1}
    assert state.press("z") == (HISTORY_TOGGLE,)


def test_modifier_polling_never_releases_observed_ctrl_shift() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.press("shift")

    calls = {"block": 0, "dispatch": []}
    screen = SimpleNamespace(
        _history_keys=state,
        _guarded_history_bindings={"history_toggle", "undo_only"},
        _history_keys_are_active=lambda: True,
        _queried_modifiers=lambda: (False, False),
        _guarded_actions=lambda actions: tuple(actions),
        _block_graph_flip=lambda: calls.__setitem__(
            "block",
            calls["block"] + 1,
        ),
        _dispatch_history_actions=lambda actions: calls[
            "dispatch"
        ].append(tuple(actions)),
    )

    HistoryKeyGuardAgentsScreen._poll_physical_modifiers(screen)

    assert state.control_down is True
    assert state.shift_down is True
    assert state.strict_undo_requested is True
    assert calls == {"block": 0, "dispatch": []}


def test_visible_agent_detail_refreshes_after_binding_change() -> None:
    selected: list[str] = []
    screen = SimpleNamespace(
        _selected_node_id="branch_1",
        _select_node=selected.append,
    )

    FinalAgentsScreen._refresh_key_binding_help(screen)

    assert selected == ["branch_1"]
