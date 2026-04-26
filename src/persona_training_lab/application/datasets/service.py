from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.repositories import DatasetsReadRepositoryPort


@dataclass(slots=True, frozen=True)
class DatasetSummary:
    dataset_id: str
    title: str
    subtitle: str
    status: str
    record_count: int
    linked_profile: str
    quality_summary: str
    readiness: str
    schema_name: str


@dataclass(slots=True)
class DatasetsService:
    datasets_repo: DatasetsReadRepositoryPort

    def list_datasets(self) -> list[DatasetSummary]:
        rows = self.datasets_repo.list_datasets()
        return [
            DatasetSummary(
                dataset_id=row.get("dataset_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                status=row.get("status", ""),
                record_count=int(row.get("record_count", 0)),
                linked_profile=row.get("linked_profile", ""),
                quality_summary=row.get("quality_summary", ""),
                readiness=row.get("readiness", ""),
                schema_name=row.get("schema_name", ""),
            )
            for row in rows
        ]
