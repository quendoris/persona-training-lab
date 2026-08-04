from __future__ import annotations

from persona_training_lab.ui.agents.screen_runtime_safe import (
    AgentsScreen as _RuntimeSafeAgentsScreen,
)


class AgentsScreen(_RuntimeSafeAgentsScreen):
    """Runtime-safe lineage with exact context navigation to tests/analysis."""

    def _open_workspace(self, workspace_key: str) -> None:
        selected_id = getattr(self, "_selected_node_id", "")
        current_id = self._state.current_node_id()
        if not current_id:
            current_id = self._graph.current_node_id()

        selected = self._context_for_node(selected_id)
        current = self._context_for_node(current_id)
        if workspace_key == "analysis":
            payload: dict[str, object] = {
                "selected": selected,
                "current": current,
            }
        else:
            payload = selected

        window = self.window()
        contextual_navigator = getattr(
            window,
            "_go_to_screen_with_context",
            None,
        )
        if callable(contextual_navigator):
            contextual_navigator(workspace_key, payload)
            return
        super()._open_workspace(workspace_key)

    def _context_for_node(self, node_id: str) -> dict[str, str]:
        context = dict(self._node_context(node_id))
        context["node_id"] = node_id
        node = self._node_by_id(node_id) if node_id else None
        if node is not None:
            context.setdefault("node_title", node.title)
            context.setdefault("node_status", node.status)

        for claim in self._runtime_claims_for_node(node_id):
            if claim.resource_kind == "model_version":
                context.setdefault("model_version_id", claim.resource_id)
            elif claim.resource_kind == "artifact_path":
                context.setdefault("artifact_path", claim.resource_id)
            elif claim.resource_kind == "training_run":
                context.setdefault("training_run_id", claim.resource_id)
            elif claim.resource_kind == "dataset":
                context.setdefault("dataset_title", claim.resource_id)
            elif claim.resource_kind == "profile":
                context.setdefault("profile_title", claim.resource_id)
            elif claim.resource_kind == "model_definition":
                context.setdefault("base_model", claim.resource_id)
        return context
