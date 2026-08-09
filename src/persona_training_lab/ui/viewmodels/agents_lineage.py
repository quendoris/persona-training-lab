from __future__ import annotations

from dataclasses import InitVar, dataclass

from persona_training_lab.application.errors.reporter import (
    ApplicationErrorReporter,
)
from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageProjectionService,
    AtomicLineageSnapshot,
)
from persona_training_lab.application.lineage.loader import LineageLoaderFactory
from persona_training_lab.ui.viewmodels.agents_overview import AgentsOverviewViewModel


@dataclass(slots=True)
class AgentsViewModel(AgentsOverviewViewModel):
    """Agents overview with worker-owned atomic lineage ports."""

    training_service: InitVar[object | None] = None
    model_versions_service: InitVar[object | None] = None
    datasets_service: InitVar[object | None] = None
    experiments_service: InitVar[object | None] = None
    lineage_projection_service: AtomicLineageProjectionService | None = None
    lineage_loader_factory: LineageLoaderFactory | None = None
    lineage_error_reporter: ApplicationErrorReporter | None = None

    def __post_init__(
        self,
        training_service: object | None,
        model_versions_service: object | None,
        datasets_service: object | None,
        experiments_service: object | None,
    ) -> None:
        del (
            training_service,
            model_versions_service,
            datasets_service,
            experiments_service,
        )
        AgentsOverviewViewModel.__post_init__(self)

    def build_lineage_snapshot(self) -> AtomicLineageSnapshot:
        service = self.lineage_projection_service
        if service is None:
            raise RuntimeError(
                "Atomic lineage projection service is not configured"
            )
        return service.build_snapshot()
