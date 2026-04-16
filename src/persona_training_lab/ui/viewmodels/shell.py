from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.workflows.supervisor import WorkflowSupervisor


@dataclass(slots=True)
class ShellViewModel:
    workflow_supervisor: WorkflowSupervisor
    current_screen: str = "dashboard"
    title: str = "Persona Training Lab"
    subtitle: str = "исследовательская станция для обучения личности"
    status_message: str = field(default="Готово")

    def navigate(self, screen: str) -> None:
        self.current_screen = screen

    def active_workflow_count(self) -> int:
        return len(self.workflow_supervisor.list_active())
