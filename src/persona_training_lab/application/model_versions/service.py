from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from persona_training_lab.application.model_versions.status_mapping import (
    normalize_model_version_status,
)
from persona_training_lab.application.ports.repositories import (
    ModelVersionsRepositoryPort,
)
from persona_training_lab.domain.models.statuses import ModelVersionStatus


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
    status_code: ModelVersionStatus = ModelVersionStatus.UNKNOWN


@dataclass(slots=True)
class ModelVersionsService:
    model_versions_repo: ModelVersionsRepositoryPort

    def list_model_versions(self) -> list[ModelVersionSummary]:
        rows = self.model_versions_repo.list_model_versions()
        summaries: list[ModelVersionSummary] = []
        for row in rows:
            status = row.get("status", "")
            summaries.append(
                ModelVersionSummary(
                    version_id=row.get("version_id", ""),
                    title=row.get("title", ""),
                    status=status,
                    base_model=row.get("base_model", ""),
                    profile_title=row.get("profile_title", ""),
                    dataset_title=row.get("dataset_title", ""),
                    training_run_id=row.get("training_run_id", ""),
                    artifact_path=row.get("artifact_path", ""),
                    quality_summary=row.get("quality_summary", ""),
                    status_code=normalize_model_version_status(status),
                )
            )
        return summaries

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
        creator = getattr(
            self.model_versions_repo,
            "create_model_version",
            None,
        )
        if creator is None or not artifact_path:
            return None

        existing = [
            item
            for item in self.list_model_versions()
            if item.training_run_id == training_run_id
        ]
        if existing:
            return existing[0]

        version_id = f"mdl_{uuid4().hex[:8]}"
        title = f"{profile_title} · {training_run_id}"
        status = ModelVersionStatus.READY.value
        normalized_quality = quality_summary.strip()
        payload = {
            "id": version_id,
            "title": title,
            "status": status,
            "base_model": base_model,
            "profile_title": profile_title,
            "dataset_title": dataset_title,
            "training_run_id": training_run_id,
            "artifact_path": artifact_path,
            "quality_summary": normalized_quality,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        creator(payload)
        return ModelVersionSummary(
            version_id=version_id,
            title=title,
            status=status,
            base_model=base_model,
            profile_title=profile_title,
            dataset_title=dataset_title,
            training_run_id=training_run_id,
            artifact_path=artifact_path,
            quality_summary=normalized_quality,
            status_code=ModelVersionStatus.READY,
        )
