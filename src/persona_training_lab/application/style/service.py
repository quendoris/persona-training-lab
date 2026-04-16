from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.repositories import UIPreferencesRepositoryPort


@dataclass(slots=True)
class StylePreferencesService:
    repository: UIPreferencesRepositoryPort

    def load_preferences(self) -> dict[str, str | None]:
        return self.repository.load()

    def save_preferences(self, preferences: dict[str, str | None]) -> None:
        self.repository.save(preferences)
