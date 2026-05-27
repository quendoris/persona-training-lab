from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4
from datetime import datetime, timezone

from persona_training_lab.application.ports.repositories import ModelVersionsReadRepositoryPort, ModelVersionsWriteRepositoryPort


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
    model_versions_repo: ModelVersionsReadRepositoryPort | ModelVersionsWriteRepositoryPort

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

    def create_from_training_run(
        self,
        *,
        training_run_id: str,
        base_model: str,
        profile_title: str,
        dataset_title: str,
        artifact_path: str,
        quality_summary: str,
    ) -> ModelVersionSummary | None:
        creator = getattr(self.model_versions_repo, "create_model_version", None)
        if creator is None or not artifact_path:
            return None

        existing = [item for item in self.list_model_versions() if item.training_run_id == training_run_id]
        if existing:
            return existing[0]

        version_id = f"mdl_{uuid4().hex[:8]}"
        title = f"{profile_title} · {training_run_id}"
        payload = {
            "id": version_id,
            "title": title,
            "status": "Готова",
            "base_model": base_model,
            "profile_title": profile_title,
            "dataset_title": dataset_title,
            "training_run_id": training_run_id,
            "artifact_path": artifact_path,
            "quality_summary": quality_summary or "Full fine-tune artifact создан и сохранён",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        creator(payload)
        return ModelVersionSummary(
            version_id=version_id,
            title=title,
            status=payload["status"],
            base_model=base_model,
            profile_title=profile_title,
            dataset_title=dataset_title,
            training_run_id=training_run_id,
            artifact_path=artifact_path,
            quality_summary=payload["quality_summary"],
        )
