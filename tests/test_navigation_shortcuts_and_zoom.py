from __future__ import annotations

import ast
from pathlib import Path

from persona_training_lab.ui.agents.atomic_lineage import (
    build_real_lineage as AtomicCompatibilityBuilder,
)
from persona_training_lab.ui.agents.atomic_lineage_public import (
    build_atomic_lineage as AtomicPublicCompatibilityBuilder,
    build_empty_lineage as EmptyPublicCompatibilityBuilder,
)
from persona_training_lab.ui.agents.lineage_presentation import (
    LineagePresentationProjection,
    ProjectedVersionNode,
    RealLineageProjection,
)
from persona_training_lab.ui.agents.lineage_projection_adapter import (
    build_atomic_lineage,
    build_empty_lineage,
)
from persona_training_lab.ui.agents.lineage_projection_legacy import (
    build_legacy_lineage,
)
from persona_training_lab.ui.agents.lineage_projection_resolver import (
    build_lineage_projection,
)
from persona_training_lab.ui.agents.real_lineage import (
    ProjectedVersionNode as RealCompatibilityNode,
    RealLineageProjection as RealCompatibilityProjection,
    build_real_lineage as LegacyCompatibilityBuilder,
)
from persona_training_lab.ui.agents.version_graph_action_menu_policy import (
    VersionGraphCanvas as ActionMenuPolicyVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_canvas_base import (
    VersionGraphCanvas as BaseVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_clean_layout import (
    VersionGraphCanvas as CleanLayoutCompatibilityCanvas,
)
from persona_training_lab.ui.agents.version_graph_curved import (
    VersionGraphCanvas as CurvedCompatibilityCanvas,
)
from persona_training_lab.ui.agents.version_graph_dynamic_workspace import (
    VersionGraphCanvas as DynamicWorkspaceCompatibilityCanvas,
)
from persona_training_lab.ui.agents.version_graph_free_zoom import (
    VersionGraphCanvas as FreeZoomVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_interactions import (
    VersionGraphCanvas as InteractionVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_layout_authority import (
    VersionGraphCanvas as LayoutAuthorityVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_layout_history import (
    VersionGraphCanvas as LayoutHistoryVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_locked import (
    VersionGraphCanvas as LockedVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_mouse_routing import (
    VersionGraphCanvas as MouseRoutingVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_persistent import (
    VersionGraphCanvas as PersistentVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_stateful import (
    VersionGraphCanvas as StatefulCompatibilityCanvas,
)
from persona_training_lab.ui.agents.version_graph_workspace_geometry import (
    VersionGraphCanvas as WorkspaceGeometryVersionGraphCanvas,
)
from persona_training_lab.ui.dashboard.screen import DashboardScreen
from persona_training_lab.ui.keybindings.definitions import AGENT_GRAPH_KEY_BINDINGS
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.shell.main_window_context import TAB_SHORTCUTS
from persona_training_lab.ui.viewmodels.dashboard import DashboardRoute


_ROOT = Path(__file__).resolve().parents[1]
_RETIRED_GRAPH_IMPLEMENTATIONS = frozenset(
    {
        "persona_training_lab.ui.agents.version_graph",
        "persona_training_lab.ui.agents.version_graph_tree",
        "persona_training_lab.ui.agents.version_graph_canvas",
        "persona_training_lab.ui.agents.version_graph_anchor",
    }
)
_HISTORICAL_GRAPH_COMPATIBILITY = frozenset(
    {
        "persona_training_lab.ui.agents.version_graph_curved",
        "persona_training_lab.ui.agents.version_graph_stateful",
        "persona_training_lab.ui.agents.version_graph_clean_layout",
        "persona_training_lab.ui.agents.version_graph_dynamic_workspace",
    }
)
_HISTORICAL_PROJECTION_COMPATIBILITY = frozenset(
    {
        "persona_training_lab.ui.agents.atomic_lineage",
        "persona_training_lab.ui.agents.atomic_lineage_public",
        "persona_training_lab.ui.agents.real_lineage",
    }
)


def _matching_imports(path: Path, modules: frozenset[str]) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in modules:
                    violations.append((node.lineno, alias.name))
            continue

        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if module in modules:
            violations.append((node.lineno, module))
        for alias in node.names:
            qualified = f"{module}.{alias.name}" if module else alias.name
            if qualified in modules:
                violations.append((node.lineno, qualified))

    return violations


def test_lineage_projection_compatibility_names_resolve_semantic_boundaries() -> None:
    assert RealLineageProjection is LineagePresentationProjection
    assert RealCompatibilityProjection is LineagePresentationProjection
    assert RealCompatibilityNode is ProjectedVersionNode
    assert AtomicCompatibilityBuilder is build_lineage_projection
    assert AtomicPublicCompatibilityBuilder is build_atomic_lineage
    assert EmptyPublicCompatibilityBuilder is build_empty_lineage
    assert LegacyCompatibilityBuilder is build_legacy_lineage


def test_production_does_not_depend_on_historical_projection_aliases() -> None:
    violations: list[str] = []

    for path in sorted((_ROOT / "src").rglob("*.py")):
        for line_number, module in _matching_imports(
            path,
            _HISTORICAL_PROJECTION_COMPATIBILITY,
        ):
            relative_path = path.relative_to(_ROOT)
            violations.append(f"{relative_path}:{line_number}: {module}")

    assert violations == [], (
        "Production still depends on historical lineage projection aliases:\n"
        + "\n".join(violations)
    )


def test_version_graph_live_mro_uses_single_responsibility_canvas_layers() -> None:
    assert FreeZoomVersionGraphCanvas.__bases__ == (
        WorkspaceGeometryVersionGraphCanvas,
    )
    assert WorkspaceGeometryVersionGraphCanvas.__bases__ == (
        MouseRoutingVersionGraphCanvas,
    )
    assert MouseRoutingVersionGraphCanvas.__bases__ == (
        ActionMenuPolicyVersionGraphCanvas,
    )
    assert ActionMenuPolicyVersionGraphCanvas.__bases__ == (
        LayoutHistoryVersionGraphCanvas,
    )
    assert LayoutHistoryVersionGraphCanvas.__bases__ == (
        LayoutAuthorityVersionGraphCanvas,
    )
    assert LayoutAuthorityVersionGraphCanvas.__bases__ == (
        InteractionVersionGraphCanvas,
    )
    assert InteractionVersionGraphCanvas.__bases__ == (LockedVersionGraphCanvas,)
    assert LockedVersionGraphCanvas.__bases__ == (PersistentVersionGraphCanvas,)
    assert PersistentVersionGraphCanvas.__bases__ == (BaseVersionGraphCanvas,)

    assert CurvedCompatibilityCanvas is BaseVersionGraphCanvas
    assert StatefulCompatibilityCanvas is InteractionVersionGraphCanvas
    assert CleanLayoutCompatibilityCanvas is ActionMenuPolicyVersionGraphCanvas
    assert DynamicWorkspaceCompatibilityCanvas is WorkspaceGeometryVersionGraphCanvas


def test_version_graph_workspace_and_mouse_routing_are_separate_layers() -> None:
    workspace_members = {
        "_workspace_geometry",
        "_content_bounds",
        "_ensure_workspace_geometry",
        "_rebuild_workspace_geometry",
        "_grow_workspace_to_current_content",
        "_apply_workspace_size",
    }
    routing_members = {
        "_MOUSE_BUTTONS",
        "_MOUSE_MODIFIERS",
        "_press_action",
        "_mouse_binding",
        "_mouse_press_matches",
        "_mouse_move_matches",
        "_wheel_matches",
        "_event_modifier_name",
        "_cancel_input_drag",
    }
    authority_members = {
        "_layout_cache_key",
        "_layout_cache",
        "_invalidate_tree_layout",
        "_layout_inputs",
        "_tree_layout",
        "_display_levels",
        "_lanes",
        "_lane_offsets",
    }
    history_members = {
        "layout_action_committed",
        "layout_snapshot",
        "restore_layout_snapshot",
        "_drag_history_before",
        "_drag_history_moved_node",
        "_drag_history_moved_subtree",
    }
    menu_policy_members = {
        "_history_action_text",
        "set_history_action_text",
        "set_undo_action_label",
        "close_node_menu",
        "_menu_actions",
    }

    assert workspace_members.isdisjoint(MouseRoutingVersionGraphCanvas.__dict__)
    assert routing_members.isdisjoint(WorkspaceGeometryVersionGraphCanvas.__dict__)
    assert history_members.isdisjoint(LayoutAuthorityVersionGraphCanvas.__dict__)
    assert menu_policy_members.isdisjoint(LayoutHistoryVersionGraphCanvas.__dict__)
    assert authority_members.isdisjoint(ActionMenuPolicyVersionGraphCanvas.__dict__)


def test_version_graph_layout_authority_has_no_shadow_algorithms() -> None:
    retired_locked_methods = {
        "_positions",
        "_max_level",
        "_display_levels",
        "_lanes",
        "_side_lane",
        "_lane_offsets",
    }
    retired_interaction_methods = {
        "_lanes",
        "_branch_groups",
        "_collect_branch_ids",
        "_choose_free_lane",
        "_candidate_lanes",
        "_lane_offsets",
        "_lane_is_free",
    }

    assert retired_locked_methods.isdisjoint(LockedVersionGraphCanvas.__dict__)
    assert retired_interaction_methods.isdisjoint(InteractionVersionGraphCanvas.__dict__)
    assert InteractionVersionGraphCanvas._lanes is BaseVersionGraphCanvas._lanes
    assert (
        FreeZoomVersionGraphCanvas._positions
        is WorkspaceGeometryVersionGraphCanvas._positions
    )
    assert (
        FreeZoomVersionGraphCanvas._display_levels
        is LayoutAuthorityVersionGraphCanvas._display_levels
    )
    assert (
        FreeZoomVersionGraphCanvas._lanes
        is LayoutAuthorityVersionGraphCanvas._lanes
    )
    assert (
        FreeZoomVersionGraphCanvas._lane_offsets
        is LayoutAuthorityVersionGraphCanvas._lane_offsets
    )


def test_retired_version_graph_implementations_are_absent_and_unreferenced() -> None:
    agents_root = _ROOT / "src" / "persona_training_lab" / "ui" / "agents"
    violations: list[str] = []

    for module in _RETIRED_GRAPH_IMPLEMENTATIONS:
        filename = f"{module.rsplit('.', 1)[-1]}.py"
        assert not (agents_root / filename).exists()

    for root_name in ("src", "tests"):
        for path in sorted((_ROOT / root_name).rglob("*.py")):
            for line_number, module in _matching_imports(
                path,
                _RETIRED_GRAPH_IMPLEMENTATIONS,
            ):
                relative_path = path.relative_to(_ROOT)
                violations.append(f"{relative_path}:{line_number}: {module}")

    assert violations == [], (
        "Retired version graph implementations are still referenced:\n"
        + "\n".join(violations)
    )


def test_production_does_not_depend_on_historical_graph_aliases() -> None:
    violations: list[str] = []

    for path in sorted((_ROOT / "src").rglob("*.py")):
        for line_number, module in _matching_imports(
            path,
            _HISTORICAL_GRAPH_COMPATIBILITY,
        ):
            relative_path = path.relative_to(_ROOT)
            violations.append(f"{relative_path}:{line_number}: {module}")

    assert violations == [], (
        "Production still depends on historical graph compatibility aliases:\n"
        + "\n".join(violations)
    )


def test_every_registered_workspace_has_unique_editable_alt_shortcut() -> None:
    expected = {
        "dashboard",
        "profiles",
        "agents",
        "datasets",
        "training",
        "snapshots",
        "tests",
        "analysis",
        "style",
        "docs",
        "keybindings",
    }
    definitions = {
        definition.binding_id: definition
        for definition in AGENT_GRAPH_KEY_BINDINGS
    }
    screens = {screen for _binding_id, screen in TAB_SHORTCUTS}
    sequences = [
        definitions[binding_id].sequence
        for binding_id, _screen in TAB_SHORTCUTS
    ]

    assert screens == expected
    assert len(sequences) == len(set(sequences))
    assert all(sequence.startswith("Alt+") for sequence in sequences)
    assert all(
        definitions[binding_id].category == "Навигация по вкладкам"
        for binding_id, _screen in TAB_SHORTCUTS
    )
    assert all(
        definitions[binding_id].editable
        for binding_id, _screen in TAB_SHORTCUTS
    )


def test_navigation_shortcut_rebinds_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "bindings.json"
    manager = KeyBindingManager(storage_path=path)

    result = manager.set_sequence("nav_agents", "Alt+G")

    assert result.accepted
    assert result.changed
    assert manager.sequence("nav_agents") == "Alt+G"
    restored = KeyBindingManager(storage_path=path)
    assert restored.sequence("nav_agents") == "Alt+G"


def test_navigation_shortcut_conflicts_are_rejected(tmp_path: Path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "bindings.json")

    result = manager.set_sequence("nav_agents", manager.sequence("nav_training"))

    assert not result.accepted
    assert result.conflict_binding_id == "nav_training"
    assert manager.sequence("nav_agents") == "Alt+A"


def test_dashboard_navigation_uses_semantic_routes_not_display_text() -> None:
    route = DashboardRoute("datasets", "focus.datasets.add")

    assert (route.screen, route.focus_key) == (
        "datasets",
        "focus.datasets.add",
    )
    assert not hasattr(DashboardScreen, "_target_for_step")
    assert not hasattr(DashboardScreen, "_lineage_target")


def test_lineage_zoom_range_is_wide_but_bounded() -> None:
    assert FreeZoomVersionGraphCanvas.MIN_ZOOM <= 0.25
    assert FreeZoomVersionGraphCanvas.MAX_ZOOM >= 8.0
    assert FreeZoomVersionGraphCanvas.ZOOM_FACTOR > 1.0
