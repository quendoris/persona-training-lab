from __future__ import annotations

from typing import Protocol


class UIPreferencesRepositoryPort(Protocol):
    def load(self) -> dict[str, str | None]: ...
    def save(self, preferences: dict[str, str | None]) -> None: ...


class ProjectsReadRepositoryPort(Protocol):
    def list_projects(self) -> list[dict[str, str]]: ...


class ProfilesReadRepositoryPort(Protocol):
    def list_profiles(self) -> list[dict[str, str]]: ...


class ProfilesWriteRepositoryPort(ProfilesReadRepositoryPort, Protocol):
    """Profiles repository that can mutate as well as read profile state."""

    def create_profile(self, payload: dict[str, str]) -> None: ...
    def update_profile(self, profile_id: str, payload: dict[str, str]) -> bool: ...


class ProfilesRepositoryPort(ProfilesWriteRepositoryPort, Protocol):
    """Full repository contract required by the profiles service."""


class AgentsReadRepositoryPort(Protocol):
    def list_agents(self) -> list[dict[str, str]]: ...


class ExperimentsReadRepositoryPort(Protocol):
    def list_experiments(self) -> list[dict[str, str]]: ...


class ExperimentsWriteRepositoryPort(ExperimentsReadRepositoryPort, Protocol):
    """Experiments repository that can mutate as well as read experiment state."""

    def create_experiment(self, payload: dict[str, str]) -> None: ...


class ExperimentsRepositoryPort(ExperimentsWriteRepositoryPort, Protocol):
    """Full repository contract required by the experiments service."""


class DatasetsReadRepositoryPort(Protocol):
    def list_datasets(self) -> list[dict[str, str | int]]: ...


class DatasetsWriteRepositoryPort(DatasetsReadRepositoryPort, Protocol):
    """Datasets repository that can mutate as well as read dataset state."""

    def add_dataset(self, payload: dict[str, str | int]) -> None: ...
    def get_dataset(self, dataset_id: str) -> dict[str, str | int] | None: ...
    def update_dataset_validation(
        self,
        dataset_id: str,
        payload: dict[str, str | int],
    ) -> None: ...


class DatasetsRepositoryPort(DatasetsWriteRepositoryPort, Protocol):
    """Full repository contract required by the datasets service."""


class TrainingReadRepositoryPort(Protocol):
    def list_training_runs(self) -> list[dict[str, str]]: ...


class TrainingWriteRepositoryPort(TrainingReadRepositoryPort, Protocol):
    """Training repository that can mutate as well as read run state."""

    def create_training_run(self, payload: dict[str, str]) -> None: ...


class TrainingRepositoryPort(TrainingWriteRepositoryPort, Protocol):
    """Full repository contract required by the training service."""


class AnalysisReadRepositoryPort(Protocol):
    def list_analysis_results(self) -> list[dict[str, str]]: ...


class ModelVersionsReadRepositoryPort(Protocol):
    def list_model_versions(self) -> list[dict[str, str]]: ...


class ModelVersionsWriteRepositoryPort(ModelVersionsReadRepositoryPort, Protocol):
    """Model-version repository that can mutate as well as read version state."""

    def create_model_version(self, payload: dict[str, str]) -> None: ...


class ModelVersionsRepositoryPort(ModelVersionsWriteRepositoryPort, Protocol):
    """Full repository contract required by the model-version service."""
