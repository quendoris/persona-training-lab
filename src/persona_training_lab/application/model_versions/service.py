from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.repositories import ModelVersionsReadRepositoryPort


@dataclass(slots=True, frozen=True)
class ModelVersionSummary:
    version_id: str
    title: str
    status: str
    base_model: str
    profile_title: str
    dataset_title: str
    training_run_id: str
    artifact_path: str
    quality_summary: str


@dataclass(slots=True)
class ModelVersionsService:
    model_versions_repo: ModelVersionsReadRepositoryPort

    def list_model_versions(self) -> list[ModelVersionSummary]:
        rows = self.model_versions_repo.list_model_versions()
        return [
            ModelVersionSummary(
                version_id=row.get("version_id", ""),
                title=row.get("title", ""),
                status=row.get("status", ""),
                base_model=row.get("base_model", ""),
                profile_title=row.get("profile_title", ""),
                dataset_title=row.get("dataset_title", ""),
                training_run_id=row.get("training_run_id", ""),
                artifact_path=row.get("artifact_path", ""),
                quality_summary=row.get("quality_summary", ""),
            )
            for row in rows
        ]
