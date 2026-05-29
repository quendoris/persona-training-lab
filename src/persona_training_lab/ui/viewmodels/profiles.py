from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.profiles.service import ProfileSummary, ProfilesService


@dataclass(slots=True, frozen=True)
class TraitView:
    name: str
    target: int
    note: str


@dataclass(slots=True, frozen=True)
class ProfileView:
    profile_id: str
    title: str
    subtitle: str
    summary: str
    communication_style: str
    principles_text: str
    constraints_text: str
    notes: str
    constraints: tuple[str, ...]
    linked_artifacts: tuple[str, ...]
    traits: tuple[TraitView, ...]
    readiness: str


@dataclass(slots=True)
class ProfilesViewModel:
    profiles_service: ProfilesService | None = None
    _profiles: tuple[ProfileView, ...] = field(default_factory=tuple)
    _current_profile_id: str = "profiles_empty"
    _message: str = ""

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self, *, select_profile_id: str | None = None) -> None:
        self._apply_profiles_connector(select_profile_id=select_profile_id)

    def _apply_profiles_connector(self, *, select_profile_id: str | None = None) -> None:
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

        mapped = tuple(self._map_summary_to_profile(summary) for summary in live_profiles)
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
        communication_style = summary.communication_style or "Не указано"
        completeness = self._completeness(summary)
        traits = (
            TraitView("Описание", 100 if summary.description.strip() else 0, "обязательное поле"),
            TraitView("Стиль", 100 if summary.communication_style.strip() else 0, "обязательное поле"),
            TraitView("Принципы", 100 if summary.principles.strip() else 0, "обязательное поле"),
            TraitView("Ограничения", 100 if summary.constraints.strip() else 0, "обязательное поле"),
        )
        return ProfileView(
            profile_id=summary.profile_id,
            title=summary.title,
            subtitle=summary.subtitle,
            summary=summary.description or summary.subtitle,
            communication_style=communication_style,
            principles_text=summary.principles,
            constraints_text=summary.constraints,
            notes=summary.notes,
            constraints=tuple(constraints_lines[:5]) if constraints_lines else ("Ограничения пока не заданы.",),
            linked_artifacts=(
                f"Стиль общения · {style_lines[0] if style_lines else 'Не указано'}",
                f"Принципы · {principles_lines[0] if principles_lines else 'Не указаны'}",
                f"Статус · {summary.status}",
            ),
            traits=traits,
            readiness=f"Структура профиля: {completeness}%",
        )

    @staticmethod
    def _parse_multiline(value: str) -> list[str]:
        return [line.strip() for line in value.splitlines() if line.strip()]

    @staticmethod
    def _completeness(summary: ProfileSummary) -> int:
        fields = [summary.title, summary.description, summary.communication_style, summary.principles, summary.constraints]
        filled = sum(1 for value in fields if value.strip())
        return int(filled / len(fields) * 100)

    @staticmethod
    def _empty_profile() -> ProfileView:
        return ProfileView(
            profile_id="profiles_empty",
            title="Профили пока не созданы",
            subtitle="Профили пока не созданы",
            summary="Профили пока не созданы",
            communication_style="",
            principles_text="",
            constraints_text="",
            notes="",
            constraints=("Создайте первый профиль, чтобы заполнить этот раздел.",),
            linked_artifacts=("Нет связанных артефактов.",),
            traits=(
                TraitView("Описание", 0, "обязательное поле"),
                TraitView("Стиль", 0, "обязательное поле"),
                TraitView("Принципы", 0, "обязательное поле"),
                TraitView("Ограничения", 0, "обязательное поле"),
            ),
            readiness="Структура профиля не заполнена",
        )

    @staticmethod
    def _error_profile() -> ProfileView:
        return ProfileView(
            profile_id="profiles_error",
            title="Не удалось загрузить профили",
            subtitle="Не удалось загрузить профили",
            summary="Не удалось загрузить профили",
            communication_style="",
            principles_text="",
            constraints_text="",
            notes="",
            constraints=("Проверьте подключение к базе данных и повторите позже.",),
            linked_artifacts=("Данные временно недоступны.",),
            traits=(
                TraitView("Описание", 0, "недоступно"),
                TraitView("Стиль", 0, "недоступно"),
                TraitView("Принципы", 0, "недоступно"),
                TraitView("Ограничения", 0, "недоступно"),
            ),
            readiness="Структура профиля недоступна",
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
            return False, "Не удалось сохранить профиль личности"
        ok, message, created = self.profiles_service.create_profile(
            title=title,
            description=description,
            communication_style=communication_style,
            principles=principles,
            constraints=constraints,
            notes=notes,
        )
        if not ok:
            return False, message

        self._message = message
        self.refresh(select_profile_id=created.profile_id if created is not None else None)
        return True, message

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
            return False, "Не удалось сохранить профиль личности"
        if self.profiles_service is None:
            return False, "Не удалось сохранить профиль личности"

        ok, message = self.profiles_service.update_profile(
            profile_id=current.profile_id,
            title=title,
            description=description,
            communication_style=communication_style,
            principles=principles,
            constraints=constraints,
            notes=notes,
        )
        if not ok:
            return False, message

        self._message = message
        self.refresh(select_profile_id=current.profile_id)
        return True, message

    def profiles(self) -> list[tuple[str, str, str]]:
        return [(p.profile_id, p.title, p.subtitle) for p in self._profiles]

    def select_profile(self, profile_id: str) -> None:
        self._current_profile_id = profile_id

    def current_profile(self) -> ProfileView:
        for profile in self._profiles:
            if profile.profile_id == self._current_profile_id:
                return profile
        return self._profiles[0]

    def header_summary(self) -> tuple[str, str]:
        profile = self.current_profile()
        if self._message:
            return profile.title, self._message
        return profile.title, profile.subtitle

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
            "title": profile.title,
            "description": profile.summary,
            "communication_style": profile.communication_style,
            "principles": profile.principles_text,
            "constraints": profile.constraints_text,
            "notes": profile.notes,
        }
