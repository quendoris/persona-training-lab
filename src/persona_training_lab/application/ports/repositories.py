from __future__ import annotations

from typing import Protocol


class UIPreferencesRepositoryPort(Protocol):
    def load(self) -> dict[str, str | None]: ...
    def save(self, preferences: dict[str, str | None]) -> None: ...


class ProjectsReadRepositoryPort(Protocol):
    def list_projects(self) -> list[dict[str, str]]: ...


class ProfilesReadRepositoryPort(Protocol):
    def list_profiles(self) -> list[dict[str, str]]: ...


class ProfilesWriteRepositoryPort(Protocol):
    def create_profile(self, payload: dict[str, str]) -> None: ...
    def update_profile(self, profile_id: str, payload: dict[str, str]) -> bool: ...


class AgentsReadRepositoryPort(Protocol):
    def list_agents(self) -> list[dict[str, str]]: ...


class ExperimentsReadRepositoryPort(Protocol):
    def list_experiments(self) -> list[dict[str, str]]: ...


class DatasetsReadRepositoryPort(Protocol):
    def list_datasets(self) -> list[dict[str, str]]: ...


class DatasetsWriteRepositoryPort(Protocol):
    def add_dataset(self, payload: dict[str, str | int]) -> None: ...
    def get_dataset(self, dataset_id: str) -> dict[str, str | int] | None: ...
    def update_dataset_validation(self, dataset_id: str, payload: dict[str, str | int]) -> None: ...


class TrainingReadRepositoryPort(Protocol):
    def list_training_runs(self) -> list[dict[str, str]]: ...


class TrainingWriteRepositoryPort(Protocol):
    def create_training_run(self, payload: dict[str, str]) -> None: ...


class AnalysisReadRepositoryPort(Protocol):
    def list_analysis_results(self) -> list[dict[str, str]]: ...


class ModelVersionsReadRepositoryPort(Protocol):
    def list_model_versions(self) -> list[dict[str, str]]: ...


class ModelVersionsWriteRepositoryPort(Protocol):
    def create_model_version(self, payload: dict[str, str]) -> None: ...
