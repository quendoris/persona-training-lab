from __future__ import annotations

import ast
from pathlib import Path

from persona_training_lab.ui.agents.version_graph_clean_layout import (
    VersionGraphCanvas as CleanLayoutVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_curved import (
    VersionGraphCanvas as CurvedVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_dynamic_workspace import (
    VersionGraphCanvas as DynamicWorkspaceVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_free_zoom import (
    VersionGraphCanvas as FreeZoomVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_locked import (
    VersionGraphCanvas as LockedVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_persistent import (
    VersionGraphCanvas as PersistentVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_stateful import (
    VersionGraphCanvas as StatefulVersionGraphCanvas,
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


def _retired_graph_imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _RETIRED_GRAPH_IMPLEMENTATIONS:
                    violations.append((node.lineno, alias.name))
            continue

        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if module in _RETIRED_GRAPH_IMPLEMENTATIONS:
            violations.append((node.lineno, module))
        for alias in node.names:
            qualified = f"{module}.{alias.name}" if module else alias.name
            if qualified in _RETIRED_GRAPH_IMPLEMENTATIONS:
                violations.append((node.lineno, qualified))

    return violations


def test_version_graph_live_mro_uses_only_current_canvas_layers() -> None:
    assert FreeZoomVersionGraphCanvas.__bases__ == (
        DynamicWorkspaceVersionGraphCanvas,
    )
    assert DynamicWorkspaceVersionGraphCanvas.__bases__ == (
        CleanLayoutVersionGraphCanvas,
    )
    assert CleanLayoutVersionGraphCanvas.__bases__ == (
        StatefulVersionGraphCanvas,
    )
    assert StatefulVersionGraphCanvas.__bases__ == (LockedVersionGraphCanvas,)
    assert LockedVersionGraphCanvas.__bases__ == (PersistentVersionGraphCanvas,)
    assert PersistentVersionGraphCanvas.__bases__ == (CurvedVersionGraphCanvas,)


def test_version_graph_layout_authority_has_no_shadow_algorithms() -> None:
    retired_locked_methods = {
        "_positions",
        "_max_level",
        "_display_levels",
        "_lanes",
        "_side_lane",
        "_lane_offsets",
    }
    retired_stateful_methods = {
        "_lanes",
        "_branch_groups",
        "_collect_branch_ids",
        "_choose_free_lane",
        "_candidate_lanes",
        "_lane_offsets",
        "_lane_is_free",
    }

    assert retired_locked_methods.isdisjoint(LockedVersionGraphCanvas.__dict__)
    assert retired_stateful_methods.isdisjoint(StatefulVersionGraphCanvas.__dict__)
    assert StatefulVersionGraphCanvas._lanes is CurvedVersionGraphCanvas._lanes
    assert FreeZoomVersionGraphCanvas._positions is DynamicWorkspaceVersionGraphCanvas._positions
    assert FreeZoomVersionGraphCanvas._display_levels is CleanLayoutVersionGraphCanvas._display_levels
    assert FreeZoomVersionGraphCanvas._lanes is CleanLayoutVersionGraphCanvas._lanes
    assert (
        FreeZoomVersionGraphCanvas._lane_offsets
        is CleanLayoutVersionGraphCanvas._lane_offsets
    )


def test_retired_version_graph_implementations_are_absent_and_unreferenced() -> None:
    agents_root = _ROOT / "src" / "persona_training_lab" / "ui" / "agents"
    violations: list[str] = []

    for module in _RETIRED_GRAPH_IMPLEMENTATIONS:
        filename = f"{module.rsplit('.', 1)[-1]}.py"
        assert not (agents_root / filename).exists()

    for root_name in ("src", "tests"):
        for path in sorted((_ROOT / root_name).rglob("*.py")):
            for line_number, module in _retired_graph_imports(path):
                relative_path = path.relative_to(_ROOT)
                violations.append(f"{relative_path}:{line_number}: {module}")

    assert violations == [], (
        "Retired version graph implementations are still referenced:\n"
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
