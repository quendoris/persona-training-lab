from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LineageDatasetRecord:
    dataset_id: str
    title: str
    status: str
    path: str
    format: str
    record_count: int
    valid_count: int
    invalid_count: int
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class LineageTrainingRunRecord:
    run_id: str
    title: str
    status: str
    base_model: str
    profile: str
    dataset_version: str
    mode: str
    progress: str
    epoch_progress: str
    loss: str
    artifact_path: str
    error_message: str
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class LineageModelVersionRecord:
    version_id: str
    title: str
    status: str
    base_model: str
    profile_title: str
    dataset_title: str
    training_run_id: str
    artifact_path: str
    quality_summary: str
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class LineageEvaluationRecord:
    experiment_id: str
    title: str
    subtitle: str
    status: str
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class LineageSourceSnapshot:
    datasets: tuple[LineageDatasetRecord, ...] = ()
    training_runs: tuple[LineageTrainingRunRecord, ...] = ()
    model_versions: tuple[LineageModelVersionRecord, ...] = ()
    evaluations: tuple[LineageEvaluationRecord, ...] = ()


class LineageSnapshotReaderPort(Protocol):
    def read_lineage_snapshot(self) -> LineageSourceSnapshot:
        """Read all lineage sources from one consistent persistence snapshot."""
