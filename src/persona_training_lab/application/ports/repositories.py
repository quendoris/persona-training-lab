from __future__ import annotations

from typing import Protocol


class UIPreferencesRepositoryPort(Protocol):
    def load(self) -> dict[str, str | None]: ...
    def save(self, preferences: dict[str, str | None]) -> None: ...
