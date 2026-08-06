from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_dynamic_workspace import (
    VersionGraphCanvas as _DynamicWorkspaceCanvas,
)


class VersionGraphCanvas(_DynamicWorkspaceCanvas):
    """Graph canvas with wide, multiplicative, pointer-anchored zoom."""

    MIN_ZOOM = 0.25
    MAX_ZOOM = 8.0
    ZOOM_FACTOR = 1.12

    def update_node_content(self, nodes) -> bool:
        """Repaint content that cannot change the cached layout footprint."""

        next_nodes = tuple(nodes)
        if self._visual_structure(self._nodes) != self._visual_structure(
            next_nodes
        ):
            return False
        self._nodes = next_nodes
        self._hit_rects.clear()
        self.update()
        return True

    @staticmethod
    def _visual_structure(nodes) -> tuple[tuple[object, ...], ...]:
        return tuple(
            (
                node.node_id,
                node.parent_id,
                node.title,
                node.level,
                node.branch_note,
                node.is_current,
            )
            for node in nodes
        )

    def wheelEvent(self, event) -> None:  # noqa: N802
        if not self._wheel_matches("zoom_canvas", event):
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return

        old_zoom = self._zoom
        factor = self.ZOOM_FACTOR if delta > 0 else 1.0 / self.ZOOM_FACTOR
        new_zoom = max(
            self.MIN_ZOOM,
            min(self.MAX_ZOOM, old_zoom * factor),
        )
        if abs(new_zoom - old_zoom) < 1e-9:
            event.accept()
            return

        anchor = event.position()
        self._set_zoom(new_zoom)
        # Emit after resizing so the scroll bars already know their new range.
        self.zoom_anchor_requested.emit(anchor, old_zoom, new_zoom)
        event.accept()

    def _set_zoom(self, zoom: float) -> None:
        self._zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, float(zoom)))
        self._refresh_size()
        self.updateGeometry()
        self.update()
