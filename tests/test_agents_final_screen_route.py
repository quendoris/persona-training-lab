from __future__ import annotations

import ast
import importlib
from pathlib import Path
from types import SimpleNamespace

from persona_training_lab.ui.agents import AgentsScreen as PublicAgentsScreen
from persona_training_lab.ui.agents.history_gesture_core import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryGestureCore,
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


_ROOT = Path(__file__).resolve().parents[1]
_RETIRED_HISTORY_MODULES = frozenset(
    {
        "history_key_state",
        "history_gesture_lifecycle",
    }
)


def _press(core: HistoryGestureCore, key_name: str):
    return core.press(
        key_name,
        observed_control=False,
        observed_shift=False,
        has_extra_modifiers=False,
        auto_repeat=False,
    )


def _retired_history_imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.rsplit(".", 1)[-1] in _RETIRED_HISTORY_MODULES:
                violations.append((node.lineno, module))
            continue

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.rsplit(".", 1)[-1] in _RETIRED_HISTORY_MODULES:
                    violations.append((node.lineno, alias.name))

    return violations


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


def test_retired_history_state_modules_have_no_importers() -> None:
    violations: list[str] = []

    for root_name in ("src", "tests"):
        for path in sorted((_ROOT / root_name).rglob("*.py")):
            for line_number, module in _retired_history_imports(path):
                relative_path = path.relative_to(_ROOT)
                violations.append(f"{relative_path}:{line_number}: {module}")

    assert violations == [], (
        "Retired history state modules are still imported:\n"
        + "\n".join(violations)
    )


def test_history_keyguard_accepts_physical_shift_release_before_next_ctrl_z() -> None:
    core = HistoryGestureCore()
    core.set_guarded_bindings({"history_toggle", "undo_only"})
    _press(core, "control")
    _press(core, "shift")
    assert _press(core, "z").actions == (HISTORY_UNDO,)
    core.release("z")

    transitions = []
    screen = SimpleNamespace(
        _history_gesture=core,
        _apply_history_transition=transitions.append,
    )

    assert HistoryKeyGuardAgentsScreen._handle_history_key_release(
        screen,
        "shift",
    ) is True
    assert core.strict_undo_requested is False
    assert len(transitions) == 1
    assert transitions[0].stop_repeat is True
    assert _press(core, "z").actions == (HISTORY_TOGGLE,)


def test_modifier_polling_never_releases_observed_ctrl_shift() -> None:
    core = HistoryGestureCore()
    core.set_guarded_bindings({"history_toggle", "undo_only"})
    _press(core, "control")
    _press(core, "shift")

    transitions = []
    screen = SimpleNamespace(
        _history_gesture=core,
        _history_keys_are_active=lambda: True,
        _queried_modifiers=lambda: (False, False),
        _apply_history_transition=transitions.append,
    )

    HistoryKeyGuardAgentsScreen._poll_physical_modifiers(screen)

    assert core.control_down is True
    assert core.shift_down is True
    assert core.strict_undo_requested is True
    assert len(transitions) == 1
    assert transitions[0].actions == ()
    assert transitions[0].claimed is False


def test_visible_agent_detail_refreshes_after_binding_change() -> None:
    selected: list[str] = []
    screen = SimpleNamespace(
        _selected_node_id="branch_1",
        _select_node=selected.append,
    )

    FinalAgentsScreen._refresh_key_binding_help(screen)

    assert selected == ["branch_1"]
