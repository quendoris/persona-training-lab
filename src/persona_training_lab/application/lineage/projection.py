from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.lineage.projection_builder import (
    build_lineage_projection,
)
from persona_training_lab.application.lineage.projection_model import (
    LineageEdge,
    LineageEntityKind,
    LineageNode,
    LineageProjection,
    LineageRelation,
    LineageSource,
    LineageSourceFailure,
    LineageState,
    UnresolvedLineageDependency,
    lineage_node_id,
)


@dataclass(slots=True)
class LineageProjectionService:
    """Read independent lineage services once, then delegate pure assembly."""

    datasets_service: object | None = None
    training_service: object | None = None
    model_versions_service: object | None = None
    experiments_service: object | None = None

    def build_projection(self) -> LineageProjection:
        failures: list[LineageSourceFailure] = []
        datasets = self._read_source(
            self.datasets_service,
            "list_datasets",
            LineageSource.DATASETS,
            failures,
        )
        runs = self._read_source(
            self.training_service,
            "list_training_runs",
            LineageSource.TRAINING,
            failures,
        )
        versions = self._read_source(
            self.model_versions_service,
            "list_model_versions",
            LineageSource.MODEL_VERSIONS,
            failures,
        )
        experiments = self._read_source(
            self.experiments_service,
            "list_experiments",
            LineageSource.EXPERIMENTS,
            failures,
        )
        return build_lineage_projection(
            datasets=datasets,
            training_runs=runs,
            model_versions=versions,
            evaluations=experiments,
            source_failures=failures,
        )

    @staticmethod
    def _read_source(
        source: object | None,
        method_name: str,
        source_name: LineageSource,
        failures: list[LineageSourceFailure],
    ) -> tuple[object, ...]:
        if source is None:
            return ()
        method = getattr(source, method_name, None)
        if not callable(method):
            failures.append(
                LineageSourceFailure(source_name, "missing_reader")
            )
            return ()
        try:
            return tuple(method())
        except Exception as error:
            failures.append(
                LineageSourceFailure(
                    source_name,
                    type(error).__name__,
                )
            )
            return ()


__all__ = (
    "LineageEdge",
    "LineageEntityKind",
    "LineageNode",
    "LineageProjection",
    "LineageProjectionService",
    "LineageRelation",
    "LineageSource",
    "LineageSourceFailure",
    "LineageState",
    "UnresolvedLineageDependency",
    "lineage_node_id",
)
