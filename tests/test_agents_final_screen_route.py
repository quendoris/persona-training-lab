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
    AgentsScreen as FinalCompatibilityAgentsScreen,
)
from persona_training_lab.ui.agents.screen_background import (
    AgentsScreen as BackgroundCompatibilityAgentsScreen,
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
from persona_training_lab.ui.agents.screen_lineage_base import (
    AgentsScreen as LineageBaseAgentsScreen,
)
from persona_training_lab.ui.agents.screen_lineage_interactions import (
    AgentsScreen as LineageInteractionAgentsScreen,
)
from persona_training_lab.ui.agents.screen_runtime_safe import (
    AgentsScreen as RuntimeSafeAgentsScreen,
)
from persona_training_lab.ui.agents.screen_stateful_fixed import (
    AgentsScreen as StatefulFixedCompatibilityAgentsScreen,
)
from persona_training_lab.ui.agents.screen_workspace_composition import (
    AgentsScreen as WorkspaceCompositionAgentsScreen,
)
from persona_training_lab.ui.agents.screen_workspace_presentation import (
    AgentsScreen as WorkspacePresentationAgentsScreen,
)


_ROOT = Path(__file__).resolve().parents[1]
_RETIRED_HISTORY_MODULES = frozenset(
    {
        "history_key_state",
        "history_gesture_lifecycle",
    }
)
_RETIRED_HISTORY_ATTRIBUTES = frozenset(
    {
        "_history_keys",
        "_history_lifecycle",
        "_guarded_history_bindings",
        "_effective_modifiers",
        "_HISTORY_BINDING_IDS",
        "_DEFAULT_GUARDED_SEQUENCES",
        "_HISTORY_SEQUENCES",
        "_disable_conflicting_history_bindings",
        "_normalized_sequence",
        "_sequence_is_history",
        "_reset_history_gesture_if_ready",
        "_sync_history_shortcut_routing",
    }
)
_RETIRED_SCREEN_IMPLEMENTATIONS = frozenset(
    {
        "persona_training_lab.ui.agents.screen",
        "persona_training_lab.ui.agents.screen_canvas",
        "persona_training_lab.ui.agents.screen_tree_canvas",
        "persona_training_lab.ui.agents.screen_layout",
        "persona_training_lab.ui.agents.screen_locked_layout",
    }
)
_RETIRED_INTERNAL_SCREEN_MODULES = frozenset(
    {
        "persona_training_lab.ui.agents.screen_stateful_fixed",
        "persona_training_lab.ui.agents.screen_agents_final",
        "persona_training_lab.ui.agents.screen_background",
    }
)
_PUBLIC_SCREEN_COMPATIBILITY_MODULES = (
    "screen",
    "screen_canvas",
    "screen_tree_canvas",
    "screen_layout",
    "screen_locked_layout",
    "screen_history_diagnostics",
)


def _press(core: HistoryGestureCore, key_name: str):
    return core.press(
        key_name,
        observed_control=False,
        observed_shift=False,
        has_extra_modifiers=False,
        auto_repeat=False,
    )


def _retired_architecture_seams(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[tuple[int, str]] = []
    is_production = path.is_relative_to(_ROOT / "src")

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.rsplit(".", 1)[-1] in _RETIRED_HISTORY_MODULES:
                violations.append((node.lineno, module))
            if module in _RETIRED_SCREEN_IMPLEMENTATIONS:
                violations.append((node.lineno, module))
            if is_production and module in _RETIRED_INTERNAL_SCREEN_MODULES:
                violations.append((node.lineno, module))
            continue

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.rsplit(".", 1)[-1] in _RETIRED_HISTORY_MODULES:
                    violations.append((node.lineno, alias.name))
                if alias.name in _RETIRED_SCREEN_IMPLEMENTATIONS:
                    violations.append((node.lineno, alias.name))
                if is_production and alias.name in _RETIRED_INTERNAL_SCREEN_MODULES:
                    violations.append((node.lineno, alias.name))
            continue

        if isinstance(node, ast.Attribute) and node.attr in _RETIRED_HISTORY_ATTRIBUTES:
            violations.append((node.lineno, node.attr))
            continue

        if isinstance(node, ast.keyword) and node.arg in _RETIRED_HISTORY_ATTRIBUTES:
            violations.append((node.lineno, node.arg))
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in _RETIRED_HISTORY_ATTRIBUTES:
                violations.append((node.lineno, node.name))
            continue

        if isinstance(node, ast.Name) and node.id in _RETIRED_HISTORY_ATTRIBUTES:
            violations.append((node.lineno, node.id))

    return violations


def test_public_agents_screen_uses_semantic_composition_layers() -> None:
    assert PublicAgentsScreen is WorkspaceCompositionAgentsScreen
    assert BackgroundCompatibilityAgentsScreen is WorkspaceCompositionAgentsScreen
    assert ContextualAgentsScreen is WorkspaceCompositionAgentsScreen
    assert FastBackgroundAgentsScreen is WorkspaceCompositionAgentsScreen
    assert ReconciledBackgroundAgentsScreen is WorkspaceCompositionAgentsScreen
    assert ReportedBackgroundAgentsScreen is WorkspaceCompositionAgentsScreen
    assert RuntimeSafeAgentsScreen is WorkspaceCompositionAgentsScreen

    assert WorkspaceCompositionAgentsScreen.__bases__ == (
        WorkspacePresentationAgentsScreen,
    )
    assert WorkspacePresentationAgentsScreen.__bases__ == (
        HistoryKeyGuardAgentsScreen,
    )
    assert HistoryKeyGuardAgentsScreen.__bases__ == (
        LineageInteractionAgentsScreen,
    )
    assert LineageInteractionAgentsScreen.__bases__ == (LineageBaseAgentsScreen,)

    assert StickyHistoryAgentsScreen is HistoryKeyGuardAgentsScreen
    assert FinalCompatibilityAgentsScreen is WorkspacePresentationAgentsScreen
    assert (
        StatefulFixedCompatibilityAgentsScreen
        is LineageInteractionAgentsScreen
    )
    assert WorkspacePresentationAgentsScreen._ROLES_MIN_WIDTH >= 280
    assert WorkspacePresentationAgentsScreen._DETAILS_MIN_WIDTH >= 360


def test_workspace_composition_owns_runtime_and_contextual_ui_adapters() -> None:
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
        assert method_name in WorkspaceCompositionAgentsScreen.__dict__
    assert "eventFilter" not in WorkspaceCompositionAgentsScreen.__dict__
    assert "_handle_history_key_release" not in WorkspaceCompositionAgentsScreen.__dict__


def test_workspace_presentation_owns_layout_without_interaction_overrides() -> None:
    assert "eventFilter" not in WorkspacePresentationAgentsScreen.__dict__
    assert "_handle_history_key_release" not in WorkspacePresentationAgentsScreen.__dict__
    assert "_poll_physical_modifiers" not in WorkspacePresentationAgentsScreen.__dict__
    assert "_reset_history_gesture" not in WorkspacePresentationAgentsScreen.__dict__


def test_lineage_interaction_layer_owns_command_and_history_effects() -> None:
    for method_name in (
        "_handle_canvas_menu_action",
        "_make_current",
        "_mark_tone",
        "_continue_from_selected",
        "_toggle_last_history_action",
        "_undo_history_only",
        "_apply_history_transition",
        "_rename_local_branch",
        "_toggle_local_branch_archive",
        "_delete_local_branch_subtree",
    ):
        assert method_name in LineageInteractionAgentsScreen.__dict__
    assert "eventFilter" not in LineageInteractionAgentsScreen.__dict__


def test_historical_public_screen_imports_are_clean_composition_aliases() -> None:
    for module_name in _PUBLIC_SCREEN_COMPATIBILITY_MODULES:
        module = importlib.import_module(
            f"persona_training_lab.ui.agents.{module_name}"
        )
        assert module.AgentsScreen is WorkspaceCompositionAgentsScreen


def test_internal_legacy_screen_paths_are_clean_semantic_aliases() -> None:
    stateful_fixed = importlib.import_module(
        "persona_training_lab.ui.agents.screen_stateful_fixed"
    )
    agents_final = importlib.import_module(
        "persona_training_lab.ui.agents.screen_agents_final"
    )
    background = importlib.import_module(
        "persona_training_lab.ui.agents.screen_background"
    )

    assert stateful_fixed.AgentsScreen is LineageInteractionAgentsScreen
    assert agents_final.AgentsScreen is WorkspacePresentationAgentsScreen
    assert background.AgentsScreen is WorkspaceCompositionAgentsScreen


def test_stateful_compatibility_path_has_one_stable_base_identity() -> None:
    module = importlib.import_module("persona_training_lab.ui.agents.screen_stateful")

    assert module.AgentsScreen is LineageBaseAgentsScreen
    assert module.AgentsScreen is not WorkspaceCompositionAgentsScreen


def test_retired_screen_implementations_are_physically_absent() -> None:
    agents_root = _ROOT / "src" / "persona_training_lab" / "ui" / "agents"

    for module in _RETIRED_SCREEN_IMPLEMENTATIONS:
        filename = f"{module.rsplit('.', 1)[-1]}.py"
        assert not (agents_root / filename).exists()


def test_retired_architecture_seams_have_no_callers() -> None:
    violations: list[str] = []

    for root_name in ("src", "tests"):
        for path in sorted((_ROOT / root_name).rglob("*.py")):
            for line_number, seam in _retired_architecture_seams(path):
                relative_path = path.relative_to(_ROOT)
                violations.append(f"{relative_path}:{line_number}: {seam}")

    assert violations == [], (
        "Retired Agents/history architecture is still referenced:\n"
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
        _apply_history_gesture_transition=transitions.append,
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
        _apply_history_gesture_transition=transitions.append,
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

    WorkspacePresentationAgentsScreen._refresh_key_binding_help(screen)

    assert selected == ["branch_1"]
