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
from persona_training_lab.ui.agents.version_graph_layout_engine import (
    LayoutInputNode,
    build_version_graph_layout,
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


_ROOT = Path(__file__).resolve().parents[1]
_RETIRED_GRAPH_IMPLEMENTATIONS = frozenset(
    {
        "persona_training_lab.ui.agents.version_graph",
        "persona_training_lab.ui.agents.version_graph_tree",
        "persona_training_lab.ui.agents.version_graph_canvas",
        "persona_training_lab.ui.agents.version_graph_anchor",
    }
)


def _widths(nodes: tuple[LayoutInputNode, ...]) -> dict[str, float]:
    return {node.node_id: max(42.0, len(node.title) * 7.0) for node in nodes}


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


def test_version_graph_layout_authority_has_no_shadow_copy_in_locked_layer() -> None:
    retired_locked_methods = {
        "_positions",
        "_max_level",
        "_display_levels",
        "_lanes",
        "_side_lane",
        "_lane_offsets",
    }

    assert retired_locked_methods.isdisjoint(LockedVersionGraphCanvas.__dict__)
    assert FreeZoomVersionGraphCanvas._positions is DynamicWorkspaceVersionGraphCanvas._positions
    assert FreeZoomVersionGraphCanvas._display_levels is CleanLayoutVersionGraphCanvas._display_levels
    assert FreeZoomVersionGraphCanvas._lanes is CleanLayoutVersionGraphCanvas._lanes
    assert FreeZoomVersionGraphCanvas._lane_offsets is CleanLayoutVersionGraphCanvas._lane_offsets


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


def test_mainline_stays_in_vertical_lane_with_side_branch_space() -> None:
    nodes = (
        LayoutInputNode("base", None, "Qwen", False),
        LayoutInputNode("training", "base", "train", False),
        LayoutInputNode("branch", "training", "branch 001", True),
        LayoutInputNode("snapshot", "training", "snapshot", False),
        LayoutInputNode("latest", "snapshot", "latest", False),
    )

    layout = build_version_graph_layout(nodes, _widths(nodes))

    assert layout.lanes["base"] == 0
    assert layout.lanes["training"] == 0
    assert layout.lanes["snapshot"] == 0
    assert layout.lanes["latest"] == 0
    assert layout.lanes["branch"] != 0
    assert layout.levels["branch"] == layout.levels["training"] + 1
    assert layout.levels["snapshot"] > layout.levels["branch"]


def test_side_branch_continuation_keeps_lane_and_does_not_jump_across_graph() -> None:
    nodes = (
        LayoutInputNode("base", None, "base", False),
        LayoutInputNode("snapshot", "base", "snapshot", False),
        LayoutInputNode("branch_010", "snapshot", "branch 010", True),
        LayoutInputNode("branch_011", "branch_010", "branch 011", True),
        LayoutInputNode("branch_012", "branch_011", "branch 012", True),
        LayoutInputNode("branch_013", "branch_012", "branch 013", True),
    )

    layout = build_version_graph_layout(nodes, _widths(nodes))

    branch_lanes = {
        layout.lanes[node.node_id]
        for node in nodes
        if node.node_id.startswith("branch_")
    }
    assert len(branch_lanes) == 1
    assert 0 not in branch_lanes


def test_side_child_branch_stays_on_parent_side_instead_of_crossing_mainline() -> None:
    nodes = (
        LayoutInputNode("base", None, "base", False),
        LayoutInputNode("snapshot", "base", "snapshot", False),
        LayoutInputNode("branch_010", "snapshot", "branch 010", True),
        LayoutInputNode("branch_011", "branch_010", "branch 011", True),
        LayoutInputNode("branch_012", "branch_011", "branch 012", True),
        LayoutInputNode("branch_013", "branch_012", "branch 013", True),
        LayoutInputNode("branch_014", "branch_013", "branch 014", True),
        LayoutInputNode("branch_015", "branch_014", "branch 015", True),
        LayoutInputNode("branch_017", "branch_015", "branch 017", True),
        LayoutInputNode("branch_016", "branch_015", "branch 016", True),
    )

    layout = build_version_graph_layout(nodes, _widths(nodes))

    assert layout.lanes["branch_016"] > 0
    assert layout.lanes["branch_017"] > 0
    assert abs(layout.lanes["branch_016"]) >= abs(layout.lanes["branch_010"])


def test_lower_overlapping_branch_gets_nearer_lane_than_long_upper_branch() -> None:
    nodes = (
        LayoutInputNode("base", None, "base", False),
        LayoutInputNode("main_1", "base", "main 1", False),
        LayoutInputNode("upper_1", "main_1", "upper long branch 1", True),
        LayoutInputNode("upper_2", "upper_1", "upper long branch 2", True),
        LayoutInputNode("upper_3", "upper_2", "upper long branch 3", True),
        LayoutInputNode("main_2", "main_1", "main 2", False),
        LayoutInputNode("lower_1", "main_2", "lower branch", True),
    )

    layout = build_version_graph_layout(nodes, _widths(nodes))

    assert abs(layout.lanes["lower_1"]) <= abs(layout.lanes["upper_1"])
    assert layout.lanes["upper_1"] != layout.lanes["lower_1"]


def test_left_lane_offset_leaves_room_for_its_label() -> None:
    nodes = (
        LayoutInputNode("base", None, "base", False),
        LayoutInputNode("main", "base", "main", False),
        LayoutInputNode("right", "main", "right branch", True),
        LayoutInputNode("left", "main", "very long left branch label", True),
    )

    layout = build_version_graph_layout(nodes, _widths(nodes))
    left_lane = layout.lanes["left"]
    if left_lane < 0:
        assert abs(layout.lane_offsets[left_lane]) > _widths(nodes)["left"]
