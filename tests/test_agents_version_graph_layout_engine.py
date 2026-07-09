from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_layout_engine import LayoutInputNode, build_version_graph_layout


def _widths(nodes: tuple[LayoutInputNode, ...]) -> dict[str, float]:
    return {node.node_id: max(42.0, len(node.title) * 7.0) for node in nodes}


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

    branch_lanes = {layout.lanes[node.node_id] for node in nodes if node.node_id.startswith("branch_")}
    assert len(branch_lanes) == 1
    assert 0 not in branch_lanes


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
