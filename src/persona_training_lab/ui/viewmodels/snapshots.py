
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SnapshotMetric:
    title: str
    value: str
    note: str


@dataclass(slots=True, frozen=True)
class SnapshotRow:
    snapshot_id: str
    title: str
    status: str
    subtitle: str


@dataclass(slots=True, frozen=True)
class TimelineItem:
    title: str
    note: str


@dataclass(slots=True)
class SnapshotsViewModel:
    snapshots: tuple[SnapshotRow, ...] = (
        SnapshotRow('snp_mia_v3_candidate', 'snp_mia_v3_candidate', 'протестирован', 'Qwen 2B · Mia core v3 · curated_rose v07'),
        SnapshotRow('snp_mia_v2_baseline', 'snp_mia_v2_baseline', 'одобрен', 'Qwen 2B · Mia core v2 · curated_rose v06'),
        SnapshotRow('snp_velvet_a1', 'snp_velvet_a1', 'архив', 'Qwen 2B · velvet analytic a1 · stress_dialogues v02'),
    )
    current_snapshot_id: str = 'snp_mia_v3_candidate'

    def select_snapshot(self, snapshot_id: str) -> None:
        self.current_snapshot_id = snapshot_id

    def current_snapshot(self) -> SnapshotRow:
        for item in self.snapshots:
            if item.snapshot_id == self.current_snapshot_id:
                return item
        return self.snapshots[0]

    @property
    def metrics(self) -> tuple[SnapshotMetric, ...]:
        if self.current_snapshot_id == 'snp_mia_v2_baseline':
            return (
                SnapshotMetric('Жизненный цикл', 'одобрен', 'старая reference-версия'),
                SnapshotMetric('Источник', 'trn_qwen2b_mia_009', 'run завершён корректно'),
                SnapshotMetric('Совпадение профиля', '0.79', 'ниже текущего кандидата'),
                SnapshotMetric('Стабильность', '0.74', 'baseline до refinement'),
            )
        if self.current_snapshot_id == 'snp_velvet_a1':
            return (
                SnapshotMetric('Жизненный цикл', 'архив', 'исследовательская боковая ветка'),
                SnapshotMetric('Источник', 'trn_qwen2b_velvet_003', 'run закрыт без развития'),
                SnapshotMetric('Совпадение профиля', '0.68', 'не подходит как основное ядро'),
                SnapshotMetric('Стабильность', '0.82', 'ровная, но эмоционально дальше'),
            )
        return (
            SnapshotMetric('Жизненный цикл', 'протестирован → review', 'готов к ручному решению'),
            SnapshotMetric('Источник', 'trn_qwen2b_mia_014', 'run завершён корректно'),
            SnapshotMetric('Совпадение профиля', '0.87', 'близко к целевому профилю'),
            SnapshotMetric('Стабильность', '0.81', 'держится под перефразами'),
        )

    @property
    def timeline(self) -> tuple[TimelineItem, ...]:
        if self.current_snapshot_id == 'snp_mia_v2_baseline':
            return (
                TimelineItem('обучение → run завершён', 'baseline-ветка была зафиксирована раньше refinement'),
                TimelineItem('freeze → manifest сохранён', 'lineage сохранён полностью'),
                TimelineItem('одобрен', 'используется как точка сравнения'),
            )
        if self.current_snapshot_id == 'snp_velvet_a1':
            return (
                TimelineItem('обучение → run завершён', 'артефакт сохранён'),
                TimelineItem('freeze', 'versioned object создан'),
                TimelineItem('архив', 'ветка оставлена как исследовательская'),
            )
        return (
            TimelineItem('обучение → run завершён', 'итоговый артефакт сохранён'),
            TimelineItem('freeze → manifest сохранён', 'lineage зафиксирован'),
            TimelineItem('тесты → psychotype pack #4', 'evaluation завершён с review notes'),
            TimelineItem('review pending', 'нужно принять решение по продвижению snapshot'),
            TimelineItem('compare ready', 'можно сравнивать с baseline-версией'),
        )

    @property
    def lineage(self) -> tuple[str, ...]:
        if self.current_snapshot_id == 'snp_mia_v2_baseline':
            return (
                'Базовая модель · Qwen 2B',
                'Профиль · Mia core v2',
                'Версия датасета · curated_rose v06',
                'Конфиг обучения · imprint_baseline',
                'Запуск обучения · trn_qwen2b_mia_009',
            )
        if self.current_snapshot_id == 'snp_velvet_a1':
            return (
                'Базовая модель · Qwen 2B',
                'Профиль · velvet analytic a1',
                'Версия датасета · stress_dialogues v02',
                'Конфиг обучения · analytic_branch',
                'Запуск обучения · trn_qwen2b_velvet_003',
            )
        return (
            'Базовая модель · Qwen 2B',
            'Профиль · Mia core v3',
            'Версия датасета · curated_rose v07',
            'Конфиг обучения · imprint_full',
            'Запуск обучения · trn_qwen2b_mia_014',
        )

    @property
    def next_step(self) -> str:
        if self.current_snapshot_id == 'snp_mia_v2_baseline':
            return 'Оставить baseline как reference-версию и сравнивать с более сильными snapshot-кандидатами.'
        if self.current_snapshot_id == 'snp_velvet_a1':
            return 'Не продвигать в основную ветку, а использовать как контрастный compare-кандидат.'
        return 'Открыть evaluation results в анализе или перевести snapshot в reviewed после ручного разбора кейсов.'
