from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Callable, Iterable

from persona_training_lab.application.datasets.status_mapping import (
    normalize_dataset_status,
)
from persona_training_lab.application.experiments.status_mapping import (
    normalize_evaluation_status,
)
from persona_training_lab.application.lineage.projection import (
    LineageProjection,
    LineageProjectionService,
)
from persona_training_lab.application.lineage.snapshot import (
    LineageSnapshotReaderPort,
    LineageSourceSnapshot,
)
from persona_training_lab.application.model_versions.status_mapping import (
    normalize_model_version_status,
)
from persona_training_lab.application.training.status_mapping import (
    normalize_training_status,
)


@dataclass(frozen=True, slots=True)
class AtomicLineageSnapshot:
    source: LineageSourceSnapshot
    projection: LineageProjection


@dataclass(slots=True)
class AtomicLineageProjectionService:
    snapshot_reader: LineageSnapshotReaderPort

    def build_snapshot(self) -> AtomicLineageSnapshot:
        source = self.snapshot_reader.read_lineage_snapshot()
        projection = LineageProjectionService(
            datasets_service=_StaticSource(
                "list_datasets",
                _with_status_codes(
                    source.datasets,
                    normalize_dataset_status,
                ),
            ),
            training_service=_StaticSource(
                "list_training_runs",
                _with_status_codes(
                    source.training_runs,
                    normalize_training_status,
                ),
            ),
            model_versions_service=_StaticSource(
                "list_model_versions",
                _with_status_codes(
                    source.model_versions,
                    normalize_model_version_status,
                ),
            ),
            experiments_service=_StaticSource(
                "list_experiments",
                _with_status_codes(
                    source.evaluations,
                    normalize_evaluation_status,
                ),
            ),
        ).build_projection()
        return AtomicLineageSnapshot(source=source, projection=projection)

    def build_projection(self) -> LineageProjection:
        return self.build_snapshot().projection


class _StaticSource:
    def __init__(
        self,
        method_name: str,
        values: tuple[object, ...],
    ) -> None:
        self._method_name = method_name
        self._values = values

    def __getattr__(self, name: str):
        if name != self._method_name:
            raise AttributeError(name)
        return lambda: self._values


def _with_status_codes(
    records: Iterable[object],
    normalizer: Callable[[object], object],
) -> tuple[object, ...]:
    result: list[object] = []
    for record in records:
        values = {
            field_name: getattr(record, field_name)
            for field_name in record.__dataclass_fields__
        }
        values["status_code"] = normalizer(values.get("status", ""))
        result.append(SimpleNamespace(**values))
    return tuple(result)
