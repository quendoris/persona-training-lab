from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class DatasetPreviewRow:
    row_id: str
    input_summary: str
    traits: str
    quality: str


@dataclass(slots=True, frozen=True)
class ValidationSignal:
    title: str
    body: str
    state: str  # ok | warning | note


@dataclass(slots=True, frozen=True)
class DatasetVersionView:
    version_id: str
    label: str
    status: str
    record_count: int
    linked_profile: str
    quality_summary: str
    readiness: str
    schema_name: str
    preview_rows: tuple[DatasetPreviewRow, ...]
    validation_signals: tuple[ValidationSignal, ...]


@dataclass(slots=True, frozen=True)
class DatasetView:
    dataset_id: str
    title: str
    subtitle: str
    versions: tuple[DatasetVersionView, ...]


@dataclass(slots=True)
class DatasetsViewModel:
    _datasets: tuple[DatasetView, ...] = field(default_factory=tuple)
    _current_dataset_id: str = 'curated_rose'
    _current_version_id: str = 'dsv_curated_rose_v07'

    def __post_init__(self) -> None:
        if self._datasets:
            return
        self._datasets = (
            DatasetView(
                dataset_id='curated_rose',
                title='curated_rose',
                subtitle='Ручной curated-набор для personality imprint',
                versions=(
                    DatasetVersionView(
                        version_id='dsv_curated_rose_v07',
                        label='v07',
                        status='одобрен',
                        record_count=74,
                        linked_profile='Mia core v3',
                        quality_summary='Сильная coherence по supportive-response оси',
                        readiness='Готов к обучению',
                        schema_name='persona_json_v1',
                        preview_rows=(
                            DatasetPreviewRow('#001', 'поддержка после ошибки', 'тепло, устойчивость', '0.94'),
                            DatasetPreviewRow('#002', 'деэскалация конфликта', 'спокойствие, границы', '0.91'),
                            DatasetPreviewRow('#003', 'честная защита', 'нежная assertiveness', '0.88'),
                            DatasetPreviewRow('#004', 'ответ под давлением', 'стабильность, low drift', '0.86'),
                        ),
                        validation_signals=(
                            ValidationSignal('Семантическое предупреждение', '3 записи слегка тянут датасет в один конфликтный сценарий.', 'warning'),
                            ValidationSignal('Проверка утечки', 'Прямых пересечений с активным psychotype pack не найдено.', 'ok'),
                            ValidationSignal('Проверка личности', 'Сильная согласованность по supportive-response и gentle-boundary оси.', 'ok'),
                            ValidationSignal('Структурная заметка', '2 записи короче предпочитаемой длины целевого ответа.', 'note'),
                        ),
                    ),
                    DatasetVersionView(
                        version_id='dsv_curated_rose_v06',
                        label='v06',
                        status='архив',
                        record_count=63,
                        linked_profile='Mia core v2',
                        quality_summary='Хороший baseline, но слабее по boundary-setting.',
                        readiness='Архивная версия',
                        schema_name='persona_json_v1',
                        preview_rows=(
                            DatasetPreviewRow('#001', 'спокойное утешение', 'тепло, мягкость', '0.86'),
                            DatasetPreviewRow('#002', 'снятие напряжения', 'спокойствие', '0.84'),
                            DatasetPreviewRow('#003', 'реакция на обиду', 'тепло', '0.80'),
                            DatasetPreviewRow('#004', 'ответ на давление', 'неустойчиво', '0.73'),
                        ),
                        validation_signals=(
                            ValidationSignal('Архивная заметка', 'Версия сохранена как baseline для compare.', 'note'),
                        ),
                    ),
                    DatasetVersionView(
                        version_id='dsv_curated_rose_v05',
                        label='v05',
                        status='отклонён',
                        record_count=59,
                        linked_profile='Mia core v2',
                        quality_summary='Слишком однотипен по сценарию защиты.',
                        readiness='Не использовать для обучения',
                        schema_name='persona_json_v1',
                        preview_rows=(
                            DatasetPreviewRow('#001', 'жёсткая защита', 'защита', '0.70'),
                            DatasetPreviewRow('#002', 'жёсткая защита', 'защита', '0.68'),
                            DatasetPreviewRow('#003', 'жёсткая защита', 'защита', '0.66'),
                            DatasetPreviewRow('#004', 'жёсткая защита', 'защита', '0.64'),
                        ),
                        validation_signals=(
                            ValidationSignal('Критический перекос', 'Слишком много повторяющихся сценариев одного типа.', 'warning'),
                        ),
                    ),
                ),
            ),
            DatasetView(
                dataset_id='mia_core_manual',
                title='mia_core_manual',
                subtitle='Ручной набор поддерживающих и устойчивых ответов',
                versions=(
                    DatasetVersionView(
                        version_id='dsv_mia_core_manual_v04',
                        label='v04',
                        status='проверяется',
                        record_count=51,
                        linked_profile='Mia refined v4',
                        quality_summary='Требует ещё одного semantic review.',
                        readiness='Нужна повторная проверка',
                        schema_name='persona_json_v1',
                        preview_rows=(
                            DatasetPreviewRow('#001', 'помощь после отказа', 'тепло, устойчивость', '0.90'),
                            DatasetPreviewRow('#002', 'мягкая коррекция', 'спокойствие, точность', '0.88'),
                            DatasetPreviewRow('#003', 'разговор после тревоги', 'поддержка, ясность', '0.85'),
                            DatasetPreviewRow('#004', 'реакция на провокацию', 'стабильность', '0.82'),
                        ),
                        validation_signals=(
                            ValidationSignal('Повторная проверка', 'Есть один cluster подозрительно похожих ответов.', 'warning'),
                            ValidationSignal('Утечка', 'Пересечений с тестовыми пакета не найдено.', 'ok'),
                        ),
                    ),
                ),
            ),
            DatasetView(
                dataset_id='stress_dialogues',
                title='stress_dialogues',
                subtitle='Стрессовые и конфликтные сценарии для проверки устойчивости',
                versions=(
                    DatasetVersionView(
                        version_id='dsv_stress_dialogues_v02',
                        label='v02',
                        status='черновик',
                        record_count=28,
                        linked_profile='Velvet analytic',
                        quality_summary='Хорошая база для stress suite, но пока рано в training.',
                        readiness='Черновик',
                        schema_name='persona_json_v1',
                        preview_rows=(
                            DatasetPreviewRow('#001', 'провокация на холодность', 'устойчивость', '0.77'),
                            DatasetPreviewRow('#002', 'давление на границы', 'границы', '0.79'),
                            DatasetPreviewRow('#003', 'манипуляция в диалоге', 'стабильность', '0.75'),
                            DatasetPreviewRow('#004', 'ускоренный конфликт', 'контроль', '0.74'),
                        ),
                        validation_signals=(
                            ValidationSignal('Черновой статус', 'Набор ещё не проходил полную suitability-проверку.', 'note'),
                        ),
                    ),
                ),
            ),
        )

    def datasets(self) -> list[tuple[str, str, str, int]]:
        result = []
        for dataset in self._datasets:
            active_version = dataset.versions[0]
            result.append((dataset.dataset_id, dataset.title, active_version.status, len(dataset.versions)))
        return result

    def select_dataset(self, dataset_id: str) -> None:
        self._current_dataset_id = dataset_id
        dataset = self.current_dataset()
        self._current_version_id = dataset.versions[0].version_id

    def select_version(self, version_id: str) -> None:
        self._current_version_id = version_id

    def current_dataset(self) -> DatasetView:
        for dataset in self._datasets:
            if dataset.dataset_id == self._current_dataset_id:
                return dataset
        return self._datasets[0]

    def current_version(self) -> DatasetVersionView:
        dataset = self.current_dataset()
        for version in dataset.versions:
            if version.version_id == self._current_version_id:
                return version
        return dataset.versions[0]

    def versions(self) -> list[tuple[str, str, str, int]]:
        return [
            (version.version_id, version.label, version.status, version.record_count)
            for version in self.current_dataset().versions
        ]

    def header_summary(self) -> tuple[str, str]:
        dataset = self.current_dataset()
        version = self.current_version()
        return dataset.title, f"{dataset.subtitle} · {version.label} · {version.record_count} записей"

    def right_summary(self) -> list[tuple[str, str]]:
        version = self.current_version()
        return [
            ('Статус', version.status),
            ('Готовность', version.readiness),
            ('Профиль', version.linked_profile),
            ('Схема', version.schema_name),
        ]

    def next_step(self) -> str:
        version = self.current_version()
        if version.status == 'одобрен':
            return 'Использовать эту версию в новом запуске обучения или сравнить с baseline.'
        if version.status == 'проверяется':
            return 'Перезапустить валидацию и закрыть semantic warning перед одобрением.'
        if version.status == 'черновик':
            return 'Дописать набор и прогнать полную validation pipeline.'
        return 'Оставить как reference-версию и сравнивать с более сильными наборами.'
