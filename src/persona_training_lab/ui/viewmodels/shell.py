from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.workflows.supervisor import WorkflowSupervisor
from persona_training_lab.ui.i18n.text import UserMessage


@dataclass(slots=True)
class ShellViewModel:
    workflow_supervisor: WorkflowSupervisor
    current_screen: str = "dashboard"
    title: UserMessage = field(
        default_factory=lambda: UserMessage("app.name")
    )
    subtitle: UserMessage = field(
        default_factory=lambda: UserMessage("app.subtitle")
    )
    status_message: UserMessage = field(
        default_factory=lambda: UserMessage("status.ready")
    )

    def navigate(self, screen: str) -> None:
        self.current_screen = screen

    def active_workflow_count(self) -> int:
        return len(self.workflow_supervisor.list_active())
