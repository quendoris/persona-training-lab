from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_locked import VersionGraphCanvas as LockableVersionGraphCanvas
from persona_training_lab.ui.viewmodels.agents import VersionNodeView


class VersionGraphCanvas(LockableVersionGraphCanvas):
    def set_nodes(self, nodes: tuple[VersionNodeView, ...]) -> None:
        self._nodes = nodes
        ids = {node.node_id for node in nodes}
        if self._selected_node_id not in ids:
            self._selected_node_id = self.current_node_id()
        self._hit_rects.clear()
        self._refresh_size()
        self.updateGeometry()
        self.update()
