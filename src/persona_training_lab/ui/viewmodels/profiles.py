from __future__ import annotations

from dataclasses import dataclass, field


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
    constraints: tuple[str, ...]
    linked_artifacts: tuple[str, ...]
    traits: tuple[TraitView, ...]


@dataclass(slots=True)
class ProfilesViewModel:
    _profiles: tuple[ProfileView, ...] = field(default_factory=tuple)
    _current_profile_id: str = 'mia_core_v3'

    def __post_init__(self) -> None:
        if self._profiles:
            return
        self._profiles = (
            ProfileView(
                profile_id='mia_core_v3',
                title='Mia core v3',
                subtitle='Тёплая, устойчивая и эмоционально читаемая personality-основа.',
                summary='Профиль с выраженным теплом, спокойной ясностью, мягкой, но устойчивой границей и низкой терпимостью к внутренним противоречиям.',
                constraints=(
                    'не уходить в холодную дистанцию',
                    'не скатываться в декоративную нежность без опоры',
                    'сохранять спокойное ведение пользователя',
                ),
                linked_artifacts=(
                    'Датасет · curated_rose v07',
                    'Training config · imprint_full_qwen',
                    'Snapshot · snp_mia_v3_candidate',
                    'Compare · v2 vs v3',
                ),
                traits=(
                    TraitView('Тепло', 88, 'считывается как опорная мягкость'),
                    TraitView('Стабильность', 81, 'хорошо держится под перефразами'),
                    TraitView('Нежная assertiveness', 74, 'границы держатся без жёсткости'),
                    TraitView('Любопытство', 92, 'живой интерес к собеседнику'),
                    TraitView('Эмоциональная устойчивость', 69, 'ещё есть запас для усиления'),
                ),
            ),
            ProfileView(
                profile_id='mia_refined_v4',
                title='Mia refined v4',
                subtitle='Уточнённый профиль с более собранной границей.',
                summary='Следующая версия профиля, где warmth остаётся высокой, но boundary-setting становится спокойнее и плотнее.',
                constraints=(
                    'не терять мягкость в конфликте',
                    'не усиливать формальную сухость',
                ),
                linked_artifacts=(
                    'Датасет · mia_core_manual v04',
                    'Evaluation · evr_psychotype_pack_04',
                ),
                traits=(
                    TraitView('Тепло', 85, 'чуть ниже, но стабильнее'),
                    TraitView('Стабильность', 84, 'выше baseline'),
                    TraitView('Нежная assertiveness', 80, 'лучше держит границы'),
                    TraitView('Любопытство', 88, 'спокойное, без суеты'),
                    TraitView('Эмоциональная устойчивость', 76, 'выше, чем у core v3'),
                ),
            ),
            ProfileView(
                profile_id='velvet_analytic_a1',
                title='Velvet analytic a1',
                subtitle='Более дистанцированный и аналитичный профиль.',
                summary='Экспериментальная ветка с высокой ясностью, меньшей эмоциональной теплотой и более наблюдательной позицией.',
                constraints=(
                    'не ломать читабельность',
                    'не уходить в холодный формализм',
                ),
                linked_artifacts=(
                    'Датасет · stress_dialogues v02',
                ),
                traits=(
                    TraitView('Тепло', 48, 'осознанно ниже'),
                    TraitView('Стабильность', 79, 'ровная аналитическая подача'),
                    TraitView('Нежная assertiveness', 62, 'спокойные границы'),
                    TraitView('Любопытство', 71, 'больше аналитики, чем вовлечения'),
                    TraitView('Эмоциональная устойчивость', 82, 'плотное ядро'),
                ),
            ),
        )

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
        return profile.title, profile.subtitle
