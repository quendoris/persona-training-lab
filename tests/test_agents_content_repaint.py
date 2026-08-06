from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.agents.lineage import LineageVersionNode
from persona_training_lab.ui.agents.version_graph_free_zoom import (
    VersionGraphCanvas,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _node(
    *,
    title: str = "Version · stable",
    subtitle: str = "loss=0.5",
    status: str = "running",
    tone: str = "pending",
    parent_id: str | None = "training",
    level: int = 3,
    branch_note: str = "current",
    is_current: bool = True,
) -> LineageVersionNode:
    return LineageVersionNode(
        node_id="snapshot",
        parent_id=parent_id,
        title=title,
        subtitle=subtitle,
        status=status,
        tone=tone,
        branch_note=branch_note,
        is_current=is_current,
        level=level,
    )


def test_content_repaint_preserves_offsets_and_workspace_geometry() -> None:
    app = _app()
    assert app is not None
    canvas = VersionGraphCanvas((_node(),))
    offset = QPointF(37.0, -19.0)
    canvas._node_offsets["snapshot"] = offset
    geometry = canvas._workspace_geometry
    assert geometry is not None

    changed = canvas.update_node_content(
        (
            _node(
                subtitle="loss=0.1",
                status="ready",
                tone="good",
            ),
        )
    )

    assert changed is True
    assert canvas._nodes[0].title == "Version · stable"
    assert canvas._nodes[0].subtitle == "loss=0.1"
    assert canvas._nodes[0].status == "ready"
    assert canvas._node_offsets["snapshot"] == offset
    assert canvas._workspace_geometry is geometry
    canvas.deleteLater()


def test_content_repaint_rejects_title_footprint_changes() -> None:
    app = _app()
    assert app is not None
    original = _node()
    canvas = VersionGraphCanvas((original,))

    changed = canvas.update_node_content(
        (_node(title="Version · a much longer renamed model version"),)
    )

    assert changed is False
    assert canvas._nodes == (original,)
    canvas.deleteLater()


def test_content_repaint_rejects_visual_structure_changes() -> None:
    app = _app()
    assert app is not None
    original = _node()
    canvas = VersionGraphCanvas((original,))

    changed = canvas.update_node_content(
        (
            _node(
                parent_id="artifact:path",
                level=4,
                branch_note="side",
                is_current=False,
            ),
        )
    )

    assert changed is False
    assert canvas._nodes == (original,)
    canvas.deleteLater()
