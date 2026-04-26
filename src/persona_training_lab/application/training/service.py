from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.repositories import TrainingReadRepositoryPort


@dataclass(slots=True, frozen=True)
class TrainingRunSummary:
    run_id: str
    title: str
    subtitle: str
    status: str
    base_model: str
    profile: str
    dataset_version: str
    mode: str
    epoch_progress: str
    loss: str
    speed: str
    checkpoints_count: str


@dataclass(slots=True)
class TrainingService:
    training_repo: TrainingReadRepositoryPort

    def list_training_runs(self) -> list[TrainingRunSummary]:
        rows = self.training_repo.list_training_runs()
        return [
            TrainingRunSummary(
                run_id=row.get("run_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                status=row.get("status", ""),
                base_model=row.get("base_model", ""),
                profile=row.get("profile", ""),
                dataset_version=row.get("dataset_version", ""),
                mode=row.get("mode", ""),
                epoch_progress=row.get("epoch_progress", ""),
                loss=row.get("loss", ""),
                speed=row.get("speed", ""),
                checkpoints_count=row.get("checkpoints_count", ""),
            )
            for row in rows
        ]
