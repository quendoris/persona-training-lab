from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.profiles.service import (
    ProfileSummary,
    ProfilesService,
)


_STATUS_ALIASES = {
    "готов": "ready",
    "готово": "ready",
    "ready": "ready",
    "активен": "active",
    "активный": "active",
    "active": "active",
    "черновик": "draft",
    "draft": "draft",
    "архивный": "archived",
    "в архиве": "archived",
    "archived": "archived",
}
_STATUS_KEYS = {
    "ready": "profiles.status.ready",
    "active": "profiles.status.active",
    "draft": "profiles.status.draft",
    "archived": "profiles.status.archived",
}
_SERVICE_MESSAGE_KEYS = {
    "Название профиля не должно быть пустым": (
        "profiles.validation.title_required"
    ),
    "Описание личности не должно быть пустым": (
        "profiles.validation.description_required"
    ),
    "Стиль общения не должен быть пустым": (
        "profiles.validation.communication_style_required"
    ),
    "Принципы профиля не должны быть пустыми": (
        "profiles.validation.principles_required"
    ),
    "Ограничения профиля не должны быть пустыми": (
        "profiles.validation.constraints_required"
    ),
    "Не удалось сохранить профиль личности": (
        "profiles.message.create_failed"
    ),
    "Профиль личности создан": "profiles.message.created",
    "Профиль личности обновлён": "profiles.message.updated",
}
_LEGACY_TEMPLATES = {
    "profiles.empty.title": "Профили пока не созданы",
    "profiles.empty.summary": "Профили личности пока не созданы.",
    "profiles.empty.constraint": (
        "Создайте первый профиль, чтобы заполнить этот раздел."
    ),
    "profiles.empty.linked": "Нет связанных артефактов.",
    "profiles.error.title": "Не удалось загрузить профили",
    "profiles.error.summary": "Не удалось загрузить профили личности.",
    "profiles.error.constraint": (
        "Проверьте подключение к базе данных и повторите позже."
    ),
    "profiles.error.linked": "Данные временно недоступны.",
    "profiles.trait.description": "Описание",
    "profiles.trait.style": "Стиль",
    "profiles.trait.principles": "Принципы",
    "profiles.trait.constraints": "Ограничения",
    "profiles.trait.required": "обязательное поле",
    "profiles.trait.unavailable": "недоступно",
    "profiles.readiness.percent": "Структура профиля: {percent}%",
    "profiles.readiness.empty": "Структура профиля не заполнена",
    "profiles.readiness.unavailable": "Структура профиля недоступна",
    "profiles.value.not_specified": "не указано",
    "profiles.value.not_specified_plural": "не указаны",
    "profiles.link.style": "Стиль общения · {value}",
    "profiles.link.principles": "Принципы · {value}",
    "profiles.link.status": "Статус · {value}",
    "profiles.status.ready": "готов",
    "profiles.status.active": "активен",
    "profiles.status.draft": "черновик",
    "profiles.status.archived": "архивный",
    "profiles.status.unknown": "{status}",
    "profiles.next.empty": (
        "Создайте профиль личности, затем подготовьте и одобрите датасет."
    ),
    "profiles.next.ready": (
        "Профиль структурно заполнен. Следующий шаг — одобрить датасет "
        "и создать запуск обучения."
    ),
    "profiles.message.create_failed": (
        "Не удалось сохранить профиль личности"
    ),
    "profiles.message.created": "Профиль личности создан",
    "profiles.message.updated": "Профиль личности обновлён",
    "profiles.validation.title_required": (
        "Название профиля не должно быть пустым"
    ),
    "profiles.validation.description_required": (
        "Описание личности не должно быть пустым"
    ),
    "profiles.validation.communication_style_required": (
        "Стиль общения не должен быть пустым"
    ),
    "profiles.validation.principles_required": (
        "Принципы профиля не должны быть пустыми"
    ),
    "profiles.validation.constraints_required": (
        "Ограничения профиля не должны быть пустыми"
    ),
    "profiles.raw": "{value}",
}


@dataclass(frozen=True, slots=True)
class ProfileText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


def profile_text(key: str, **values: object) -> ProfileText:
    return ProfileText(key, MappingProxyType(dict(values)))


@dataclass(slots=True, frozen=True)
class TraitView:
    name: ProfileText
    target: int
    note: ProfileText


@dataclass(slots=True, frozen=True)
class ProfileView:
    profile_id: str
    title: str | ProfileText
    subtitle: str | ProfileText
    summary: str | ProfileText
    communication_style: str
    principles_text: str
    constraints_text: str
    notes: str
    constraints: tuple[str | ProfileText, ...]
    linked_artifacts: tuple[ProfileText, ...]
    traits: tuple[TraitView, ...]
    readiness: ProfileText
    readiness_code: str
    completeness: int
    status_code: str


@dataclass(slots=True)
class ProfilesViewModel:
    profiles_service: ProfilesService | None = None
    _profiles: tuple[ProfileView, ...] = field(default_factory=tuple)
    _current_profile_id: str = "profiles_empty"
    _message: ProfileText | None = None
    _legacy_message: str = ""

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self, *, select_profile_id: str | None = None) -> None:
        self._apply_profiles_connector(select_profile_id=select_profile_id)

    def _apply_profiles_connector(
        self,
        *,
        select_profile_id: str | None = None,
    ) -> None:
        if self.profiles_service is None:
            self._profiles = (self._empty_profile(),)
            self._current_profile_id = self._profiles[0].profile_id
            return
        try:
            live_profiles = self.profiles_service.list_profiles()
        except Exception:
            self._profiles = (self._error_profile(),)
            self._current_profile_id = self._profiles[0].profile_id
            return

        if not live_profiles:
            self._profiles = (self._empty_profile(),)
            self._current_profile_id = self._profiles[0].profile_id
            return

        mapped = tuple(
            self._map_summary_to_profile(summary)
            for summary in live_profiles
        )
        self._profiles = mapped
        if select_profile_id is not None:
            for profile in mapped:
                if profile.profile_id == select_profile_id:
                    self._current_profile_id = profile.profile_id
                    return
        self._current_profile_id = mapped[0].profile_id

    def _map_summary_to_profile(self, summary: ProfileSummary) -> ProfileView:
        constraints_lines = self._parse_multiline(summary.constraints)
        principles_lines = self._parse_multiline(summary.principles)
        style_lines = self._parse_multiline(summary.communication_style)
        completeness = self._completeness(summary)
        status_code = self.normalize_status(summary.status)
        traits = self._trait_views(
            description=bool(summary.description.strip()),
            communication_style=bool(summary.communication_style.strip()),
            principles=bool(summary.principles.strip()),
            constraints=bool(summary.constraints.strip()),
        )
        style_value: str | ProfileText = (
            style_lines[0]
            if style_lines
            else profile_text("profiles.value.not_specified")
        )
        principles_value: str | ProfileText = (
            principles_lines[0]
            if principles_lines
            else profile_text("profiles.value.not_specified_plural")
        )
        return ProfileView(
            profile_id=summary.profile_id,
            title=summary.title,
            subtitle=(
                summary.subtitle
                or profile_text("profiles.header.subtitle")
            ),
            summary=(
                summary.description
                or summary.subtitle
                or profile_text("profiles.value.not_specified")
            ),
            communication_style=summary.communication_style,
            principles_text=summary.principles,
            constraints_text=summary.constraints,
            notes=summary.notes,
            constraints=(
                tuple(constraints_lines[:5])
                if constraints_lines
                else (profile_text("profiles.value.not_specified_plural"),)
            ),
            linked_artifacts=(
                profile_text("profiles.link.style", value=style_value),
                profile_text(
                    "profiles.link.principles",
                    value=principles_value,
                ),
                profile_text(
                    "profiles.link.status",
                    value=self.status_text(summary.status),
                ),
            ),
            traits=traits,
            readiness=profile_text(
                "profiles.readiness.percent",
                percent=completeness,
            ),
            readiness_code=("ready" if completeness == 100 else "incomplete"),
            completeness=completeness,
            status_code=status_code,
        )

    @staticmethod
    def _trait_views(
        *,
        description: bool,
        communication_style: bool,
        principles: bool,
        constraints: bool,
        unavailable: bool = False,
    ) -> tuple[TraitView, ...]:
        note_key = (
            "profiles.trait.unavailable"
            if unavailable
            else "profiles.trait.required"
        )
        return (
            TraitView(
                profile_text("profiles.trait.description"),
                100 if description else 0,
                profile_text(note_key),
            ),
            TraitView(
                profile_text("profiles.trait.style"),
                100 if communication_style else 0,
                profile_text(note_key),
            ),
            TraitView(
                profile_text("profiles.trait.principles"),
                100 if principles else 0,
                profile_text(note_key),
            ),
            TraitView(
                profile_text("profiles.trait.constraints"),
                100 if constraints else 0,
                profile_text(note_key),
            ),
        )

    @staticmethod
    def _parse_multiline(value: str) -> list[str]:
        return [line.strip() for line in value.splitlines() if line.strip()]

    @staticmethod
    def _completeness(summary: ProfileSummary) -> int:
        fields = [
            summary.title,
            summary.description,
            summary.communication_style,
            summary.principles,
            summary.constraints,
        ]
        filled = sum(1 for value in fields if value.strip())
        return int(filled / len(fields) * 100)

    @classmethod
    def _empty_profile(cls) -> ProfileView:
        return ProfileView(
            profile_id="profiles_empty",
            title=profile_text("profiles.empty.title"),
            subtitle=profile_text("profiles.empty.summary"),
            summary=profile_text("profiles.empty.summary"),
            communication_style="",
            principles_text="",
            constraints_text="",
            notes="",
            constraints=(profile_text("profiles.empty.constraint"),),
            linked_artifacts=(profile_text("profiles.empty.linked"),),
            traits=cls._trait_views(
                description=False,
                communication_style=False,
                principles=False,
                constraints=False,
            ),
            readiness=profile_text("profiles.readiness.empty"),
            readiness_code="empty",
            completeness=0,
            status_code="empty",
        )

    @classmethod
    def _error_profile(cls) -> ProfileView:
        return ProfileView(
            profile_id="profiles_error",
            title=profile_text("profiles.error.title"),
            subtitle=profile_text("profiles.error.summary"),
            summary=profile_text("profiles.error.summary"),
            communication_style="",
            principles_text="",
            constraints_text="",
            notes="",
            constraints=(profile_text("profiles.error.constraint"),),
            linked_artifacts=(profile_text("profiles.error.linked"),),
            traits=cls._trait_views(
                description=False,
                communication_style=False,
                principles=False,
                constraints=False,
                unavailable=True,
            ),
            readiness=profile_text("profiles.readiness.unavailable"),
            readiness_code="unavailable",
            completeness=0,
            status_code="unavailable",
        )

    def create_profile(
        self,
        *,
        title: str,
        description: str,
        communication_style: str,
        principles: str,
        constraints: str,
        notes: str,
    ) -> tuple[bool, str]:
        if self.profiles_service is None:
            return self._set_action_result(
                False,
                profile_text("profiles.message.create_failed"),
                "Не удалось сохранить профиль личности",
            )
        ok, message, created = self.profiles_service.create_profile(
            title=title,
            description=description,
            communication_style=communication_style,
            principles=principles,
            constraints=constraints,
            notes=notes,
        )
        semantic = self._service_message_text(
            message,
            fallback=(
                "profiles.message.created"
                if ok
                else "profiles.message.create_failed"
            ),
        )
        self._set_action_result(ok, semantic, message)
        if ok:
            self.refresh(
                select_profile_id=(
                    created.profile_id if created is not None else None
                )
            )
        return ok, message

    def update_current_profile(
        self,
        *,
        title: str,
        description: str,
        communication_style: str,
        principles: str,
        constraints: str,
        notes: str,
    ) -> tuple[bool, str]:
        current = self.current_profile()
        if current.profile_id in {"profiles_empty", "profiles_error"}:
            return self._set_action_result(
                False,
                profile_text("profiles.message.create_failed"),
                "Не удалось сохранить профиль личности",
            )
        if self.profiles_service is None:
            return self._set_action_result(
                False,
                profile_text("profiles.message.create_failed"),
                "Не удалось сохранить профиль личности",
            )

        ok, message = self.profiles_service.update_profile(
            profile_id=current.profile_id,
            title=title,
            description=description,
            communication_style=communication_style,
            principles=principles,
            constraints=constraints,
            notes=notes,
        )
        semantic = self._service_message_text(
            message,
            fallback=(
                "profiles.message.updated"
                if ok
                else "profiles.message.create_failed"
            ),
        )
        self._set_action_result(ok, semantic, message)
        if ok:
            self.refresh(select_profile_id=current.profile_id)
        return ok, message

    def _set_action_result(
        self,
        ok: bool,
        message: ProfileText,
        legacy: str,
    ) -> tuple[bool, str]:
        self._message = message
        self._legacy_message = legacy
        return ok, legacy

    @staticmethod
    def _service_message_text(
        message: str,
        *,
        fallback: str,
    ) -> ProfileText:
        key = _SERVICE_MESSAGE_KEYS.get(message)
        if key is not None:
            return profile_text(key)
        if message:
            return profile_text("profiles.raw", value=message)
        return profile_text(fallback)

    def profile_views(self) -> tuple[ProfileView, ...]:
        return self._profiles

    def profiles(self) -> list[tuple[str, str, str]]:
        return [
            (
                profile.profile_id,
                self._legacy_render(profile.title),
                self._legacy_render(profile.subtitle),
            )
            for profile in self._profiles
        ]

    def select_profile(self, profile_id: str) -> None:
        self._current_profile_id = profile_id

    def current_profile(self) -> ProfileView:
        for profile in self._profiles:
            if profile.profile_id == self._current_profile_id:
                return profile
        return self._profiles[0]

    def header_summary_model(
        self,
    ) -> tuple[str | ProfileText, str | ProfileText]:
        profile = self.current_profile()
        if self._message is not None:
            return profile.title, self._message
        return profile.title, profile.subtitle

    def header_summary(self) -> tuple[str, str]:
        title, subtitle = self.header_summary_model()
        return self._legacy_render(title), self._legacy_render(subtitle)

    def next_step_model(self) -> ProfileText:
        profile = self.current_profile()
        if profile.profile_id in {"profiles_empty", "profiles_error"}:
            return profile_text("profiles.next.empty")
        return profile_text("profiles.next.ready")

    def current_message(self) -> ProfileText | None:
        return self._message

    @staticmethod
    def normalize_status(status: str) -> str:
        normalized = status.strip().casefold()
        return _STATUS_ALIASES.get(normalized, "unknown")

    def status_text(self, status: str) -> ProfileText:
        code = self.normalize_status(status)
        key = _STATUS_KEYS.get(code)
        if key is not None:
            return profile_text(key)
        raw: str | ProfileText = (
            status.strip()
            if status.strip()
            else profile_text("profiles.value.not_specified")
        )
        return profile_text("profiles.status.unknown", status=raw)

    def profile_form_data(self) -> dict[str, str]:
        profile = self.current_profile()
        if profile.profile_id in {"profiles_empty", "profiles_error"}:
            return {
                "title": "",
                "description": "",
                "communication_style": "",
                "principles": "",
                "constraints": "",
                "notes": "",
            }
        return {
            "title": self._raw_text(profile.title),
            "description": self._raw_text(profile.summary),
            "communication_style": profile.communication_style,
            "principles": profile.principles_text,
            "constraints": profile.constraints_text,
            "notes": profile.notes,
        }

    @staticmethod
    def _raw_text(value: str | ProfileText) -> str:
        return value if isinstance(value, str) else ""

    @classmethod
    def _legacy_render(cls, value: object) -> str:
        if not isinstance(value, ProfileText):
            return str(value)
        rendered_values = {
            key: cls._legacy_render(item)
            for key, item in value.values.items()
        }
        template = _LEGACY_TEMPLATES.get(value.key)
        if template is None:
            return str(rendered_values.get("value", value.key))
        return template.format_map(rendered_values)
