from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from persona_training_lab.application.messages import ActionResult
from persona_training_lab.application.ports.repositories import ProfilesRepositoryPort
from persona_training_lab.domain.persona.statuses import ProfileStatus


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
    profiles_repo: ProfilesRepositoryPort

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
    ) -> tuple[ActionResult, ProfileSummary | None]:
        validation = self._validate_inputs(
            title=title,
            description=description,
            communication_style=communication_style,
            principles=principles,
            constraints=constraints,
        )
        if not validation.ok:
            return validation, None

        now = datetime.now(timezone.utc).isoformat()
        profile_id = f"prf_{uuid4().hex[:8]}"
        payload = {
            "id": profile_id,
            "title": self._normalize_text(title, 120),
            "subtitle": self._normalize_text(description, 180),
            "description": self._normalize_text(description, 2000),
            "communication_style": self._normalize_text(
                communication_style,
                2000,
            ),
            "principles": self._normalize_text(principles, 3000),
            "constraints": self._normalize_text(constraints, 3000),
            "notes": self._normalize_text(notes, 3000),
            "status": ProfileStatus.READY.value,
            "created_at": now,
            "updated_at": now,
        }
        try:
            create_method = getattr(self.profiles_repo, "create_profile", None)
            if create_method is None:
                return ActionResult(False, "save_failed"), None
            create_method(payload)
        except Exception:
            return ActionResult(False, "save_failed"), None

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
        return ActionResult(True, "created"), created

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
    ) -> ActionResult:
        validation = self._validate_inputs(
            title=title,
            description=description,
            communication_style=communication_style,
            principles=principles,
            constraints=constraints,
        )
        if not validation.ok:
            return validation
        if not profile_id.strip():
            return ActionResult(False, "save_failed")

        payload = {
            "title": self._normalize_text(title, 120),
            "subtitle": self._normalize_text(description, 180),
            "description": self._normalize_text(description, 2000),
            "communication_style": self._normalize_text(
                communication_style,
                2000,
            ),
            "principles": self._normalize_text(principles, 3000),
            "constraints": self._normalize_text(constraints, 3000),
            "notes": self._normalize_text(notes, 3000),
            "status": ProfileStatus.READY.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            update_method = getattr(self.profiles_repo, "update_profile", None)
            if update_method is None:
                return ActionResult(False, "save_failed")
            updated = bool(update_method(profile_id, payload))
        except Exception:
            return ActionResult(False, "save_failed")

        if not updated:
            return ActionResult(False, "save_failed")
        return ActionResult(True, "updated")

    def _validate_inputs(
        self,
        *,
        title: str,
        description: str,
        communication_style: str,
        principles: str,
        constraints: str,
    ) -> ActionResult:
        required_fields = (
            (title, "title_required"),
            (description, "description_required"),
            (communication_style, "communication_style_required"),
            (principles, "principles_required"),
            (constraints, "constraints_required"),
        )
        for value, code in required_fields:
            if not value.strip():
                return ActionResult(False, code)
        return ActionResult(True, "valid")

    def _normalize_text(self, value: str, max_len: int) -> str:
        text = value.strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"
