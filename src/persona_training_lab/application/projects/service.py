from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.repositories import ProjectsReadRepositoryPort


@dataclass(slots=True, frozen=True)
class ProjectSummary:
    project_id: str
    title: str
    status: str


@dataclass(slots=True)
class ProjectsService:
    projects_repo: ProjectsReadRepositoryPort

    def list_projects(self) -> list[ProjectSummary]:
        rows = self.projects_repo.list_projects()
        return [
            ProjectSummary(
                project_id=row.get("project_id", ""),
                title=row.get("title", ""),
                status=row.get("status", ""),
            )
            for row in rows
        ]
