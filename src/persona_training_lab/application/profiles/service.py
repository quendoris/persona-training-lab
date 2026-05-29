from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from persona_training_lab.application.ports.repositories import ProfilesReadRepositoryPort, ProfilesWriteRepositoryPort


@dataclass(slots=True, frozen=True)
class ProfileSummary:
    profile_id: str
    title: str
    subtitle: str
    description: str
    communication_style: str
    principles: str
    constraints: str
    notes: str
    status: str


@dataclass(slots=True)
class ProfilesService:
    profiles_repo: ProfilesReadRepositoryPort | ProfilesWriteRepositoryPort

    def list_profiles(self) -> list[ProfileSummary]:
        rows = self.profiles_repo.list_profiles()
        return [
            ProfileSummary(
                profile_id=row.get("profile_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                description=row.get("description", row.get("subtitle", "")),
                communication_style=row.get("communication_style", ""),
                principles=row.get("principles", ""),
                constraints=row.get("constraints", ""),
                notes=row.get("notes", ""),
                status=row.get("status", ""),
            )
            for row in rows
        ]

    def create_profile(
        self,
        *,
        title: str,
        description: str,
        communication_style: str,
        principles: str,
        constraints: str,
        notes: str,
    ) -> tuple[bool, str, ProfileSummary | None]:
        valid, message = self._validate_inputs(
            title=title,
            description=description,
            communication_style=communication_style,
            principles=principles,
            constraints=constraints,
        )
        if not valid:
            return False, message, None

        now = datetime.now(timezone.utc).isoformat()
        profile_id = f"prf_{uuid4().hex[:8]}"
        payload = {
            "id": profile_id,
            "title": self._normalize_text(title, 120),
            "subtitle": self._normalize_text(description, 180),
            "description": self._normalize_text(description, 2000),
            "communication_style": self._normalize_text(communication_style, 2000),
            "principles": self._normalize_text(principles, 3000),
            "constraints": self._normalize_text(constraints, 3000),
            "notes": self._normalize_text(notes, 3000),
            "status": "готов",
            "created_at": now,
            "updated_at": now,
        }
        try:
            create_method = getattr(self.profiles_repo, "create_profile", None)
            if create_method is None:
                return False, "Не удалось сохранить профиль личности", None
            create_method(payload)
        except Exception:
            return False, "Не удалось сохранить профиль личности", None

        created = ProfileSummary(
            profile_id=payload["id"],
            title=payload["title"],
            subtitle=payload["subtitle"],
            description=payload["description"],
            communication_style=payload["communication_style"],
            principles=payload["principles"],
            constraints=payload["constraints"],
            notes=payload["notes"],
            status=payload["status"],
        )
        return True, "Профиль личности создан", created

    def update_profile(
        self,
        *,
        profile_id: str,
        title: str,
        description: str,
        communication_style: str,
        principles: str,
        constraints: str,
        notes: str,
    ) -> tuple[bool, str]:
        valid, message = self._validate_inputs(
            title=title,
            description=description,
            communication_style=communication_style,
            principles=principles,
            constraints=constraints,
        )
        if not valid:
            return False, message
        if not profile_id.strip():
            return False, "Не удалось сохранить профиль личности"

        payload = {
            "title": self._normalize_text(title, 120),
            "subtitle": self._normalize_text(description, 180),
            "description": self._normalize_text(description, 2000),
            "communication_style": self._normalize_text(communication_style, 2000),
            "principles": self._normalize_text(principles, 3000),
            "constraints": self._normalize_text(constraints, 3000),
            "notes": self._normalize_text(notes, 3000),
            "status": "готов",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            update_method = getattr(self.profiles_repo, "update_profile", None)
            if update_method is None:
                return False, "Не удалось сохранить профиль личности"
            updated = bool(update_method(profile_id, payload))
        except Exception:
            return False, "Не удалось сохранить профиль личности"

        if not updated:
            return False, "Не удалось сохранить профиль личности"
        return True, "Профиль личности обновлён"

    def _validate_inputs(
        self,
        *,
        title: str,
        description: str,
        communication_style: str,
        principles: str,
        constraints: str,
    ) -> tuple[bool, str]:
        required_fields = (
            (title, "Название профиля не должно быть пустым"),
            (description, "Описание личности не должно быть пустым"),
            (communication_style, "Стиль общения не должен быть пустым"),
            (principles, "Принципы профиля не должны быть пустыми"),
            (constraints, "Ограничения профиля не должны быть пустыми"),
        )
        for value, message in required_fields:
            if not value.strip():
                return False, message
        return True, ""

    def _normalize_text(self, value: str, max_len: int) -> str:
        text = value.strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"
