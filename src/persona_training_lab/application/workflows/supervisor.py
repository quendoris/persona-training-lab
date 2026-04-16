from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.workflows.state import WorkflowRuntimeState


@dataclass(slots=True)
class WorkflowSupervisor:
    _active: dict[str, WorkflowRuntimeState] = field(default_factory=dict)

    def register(self, state: WorkflowRuntimeState) -> None:
        self._active[state.workflow_id] = state

    def finish(self, workflow_id: str) -> None:
        self._active.pop(workflow_id, None)

    def list_active(self) -> list[WorkflowRuntimeState]:
        return list(self._active.values())
