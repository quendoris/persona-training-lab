from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.repositories import ProfilesReadRepositoryPort


@dataclass(slots=True, frozen=True)
class ProfileSummary:
    profile_id: str
    title: str
    subtitle: str
    status: str


@dataclass(slots=True)
class ProfilesService:
    profiles_repo: ProfilesReadRepositoryPort

    def list_profiles(self) -> list[ProfileSummary]:
        rows = self.profiles_repo.list_profiles()
        return [
            ProfileSummary(
                profile_id=row.get("profile_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                status=row.get("status", ""),
            )
            for row in rows
        ]
