from __future__ import annotations

from typing import Protocol


class UIPreferencesRepositoryPort(Protocol):
    def load(self) -> dict[str, str | None]: ...
    def save(self, preferences: dict[str, str | None]) -> None: ...


class ProjectsReadRepositoryPort(Protocol):
    def list_projects(self) -> list[dict[str, str]]: ...


class ProfilesReadRepositoryPort(Protocol):
    def list_profiles(self) -> list[dict[str, str]]: ...


class AgentsReadRepositoryPort(Protocol):
    def list_agents(self) -> list[dict[str, str]]: ...


class ExperimentsReadRepositoryPort(Protocol):
    def list_experiments(self) -> list[dict[str, str]]: ...


class DatasetsReadRepositoryPort(Protocol):
    def list_datasets(self) -> list[dict[str, str]]: ...
