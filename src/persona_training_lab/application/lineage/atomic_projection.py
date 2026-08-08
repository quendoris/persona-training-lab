from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from types import SimpleNamespace
from typing import Callable, Iterable

from persona_training_lab.application.datasets.status_mapping import (
    normalize_dataset_status,
)
from persona_training_lab.application.experiments.status_mapping import (
    normalize_evaluation_status,
)
from persona_training_lab.application.lineage.projection_builder import (
    build_lineage_projection,
)
from persona_training_lab.application.lineage.projection_model import (
    LineageProjection,
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
        projection = build_lineage_projection(
            datasets=_with_status_codes(
                source.datasets,
                normalize_dataset_status,
            ),
            training_runs=_with_status_codes(
                source.training_runs,
                normalize_training_status,
            ),
            model_versions=_with_status_codes(
                source.model_versions,
                normalize_model_version_status,
            ),
            evaluations=_with_status_codes(
                source.evaluations,
                normalize_evaluation_status,
            ),
        )
        return AtomicLineageSnapshot(source=source, projection=projection)

    def build_projection(self) -> LineageProjection:
        return self.build_snapshot().projection


def _with_status_codes(
    records: Iterable[object],
    normalizer: Callable[[object], object],
) -> tuple[object, ...]:
    result: list[object] = []
    for record in records:
        if not is_dataclass(record) or isinstance(record, type):
            raise TypeError(
                "Lineage snapshot records must be dataclass instances"
            )
        values = {
            item.name: getattr(record, item.name)
            for item in fields(record)
        }
        values["status_code"] = normalizer(values.get("status", ""))
        result.append(SimpleNamespace(**values))
    return tuple(result)
