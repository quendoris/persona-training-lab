from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from persona_training_lab.application.agents.service import AgentsService
from persona_training_lab.application.analysis.service import AnalysisService
from persona_training_lab.application.automation import AutomationService
from persona_training_lab.application.automation.audit import AutomationAuditTrail
from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.application.errors.reporter import ApplicationErrorReporter
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.lineage.loader import LineageLoaderFactory
from persona_training_lab.application.lineage.runtime_safety import LineageRuntimeSafety
from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.operations_center import OperationsCenterService
from persona_training_lab.application.projects.service import ProjectsService
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.runtime.atomic import (
    RuntimeOperationCoordinator,
)
from persona_training_lab.application.style.service import StylePreferencesService
from persona_training_lab.application.telemetry.service import SystemTelemetryService
from persona_training_lab.application.training.full_backend import (
    LocalFullFineTuneBackend,
)
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.application.workflows.supervisor import WorkflowSupervisor
from persona_training_lab.config.app_settings import AppSettings
from persona_training_lab.config.paths import (
    build_workspace_paths,
    ensure_workspace_dirs,
)
from persona_training_lab.infrastructure.artifacts.manager import LocalArtifactManager
from persona_training_lab.infrastructure.automation import FilesystemAutomationRecipeProvider
from persona_training_lab.infrastructure.local_model.probe_provider import (
    FilesystemLocalModelProbeProvider,
)
from persona_training_lab.infrastructure.logging.structured import configure_logging
from persona_training_lab.infrastructure.persistence.lineage_loader import (
    SQLiteLineageProjectionLoader,
)
from persona_training_lab.infrastructure.persistence.repositories.agents import (
    SQLiteAgentsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.analysis import (
    SQLiteAnalysisRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.datasets import (
    SQLiteDatasetsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.event_log import (
    SQLiteEventLogRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.experiments import (
    SQLiteExperimentsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.lineage_resource_links import (
    SQLiteLineageResourceLinksRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.model_versions import (
    SQLiteModelVersionsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.profiles import (
    SQLiteProfilesRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.projects import (
    SQLiteProjectsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.runtime_operations_atomic import (
    SQLiteRuntimeOperationsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.training import (
    SQLiteTrainingRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.ui_preferences import (
    SQLiteUIPreferencesRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.db import SQLiteDatabase
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.infrastructure.telemetry.collector import (
    NvidiaSmiTelemetryProvider,
    PsutilTelemetryProvider,
)
from persona_training_lab.ui.viewmodels.agents_lineage import AgentsViewModel
from persona_training_lab.ui.viewmodels.analysis_lineage import AnalysisViewModel
from persona_training_lab.ui.viewmodels.automation import AutomationViewModel
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel
from persona_training_lab.ui.viewmodels.datasets import DatasetsViewModel
from persona_training_lab.ui.viewmodels.docs import DocsViewModel
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel
from persona_training_lab.ui.viewmodels.shell import ShellViewModel
from persona_training_lab.ui.viewmodels.snapshots import SnapshotsViewModel
from persona_training_lab.ui.viewmodels.style import StyleViewModel
from persona_training_lab.ui.viewmodels.telemetry import TelemetryViewModel
from persona_training_lab.ui.viewmodels.tests_lineage import TestsViewModel
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    shell_vm: ShellViewModel
    dashboard_vm: DashboardViewModel
    docs_vm: DocsViewModel
    style_vm: StyleViewModel
    datasets_vm: DatasetsViewModel
    profiles_vm: ProfilesViewModel
    agents_vm: AgentsViewModel
    training_vm: TrainingViewModel
    snapshots_vm: SnapshotsViewModel
    tests_vm: TestsViewModel
    analysis_vm: AnalysisViewModel
    automation_vm: AutomationViewModel
    telemetry_vm: TelemetryViewModel
    runtime_operations: RuntimeOperationCoordinator
    lineage_loader_factory: LineageLoaderFactory
    lineage_runtime_safety: LineageRuntimeSafety
    operations_center: OperationsCenterService
    error_reporter: ApplicationErrorReporter


def build_container() -> AppContainer:
    settings = AppSettings()
    paths = build_workspace_paths(settings)
    ensure_workspace_dirs(paths)
    configure_logging(paths.root / "logs")

    db = SQLiteDatabase(paths.sqlite_db)
    connection = db.connect()
    create_minimal_schema(connection)
    lineage_loader_factory: LineageLoaderFactory = partial(
        SQLiteLineageProjectionLoader,
        paths.sqlite_db,
    )

    artifact_manager = LocalArtifactManager(paths)
    artifact_manager.ensure_layout()

    ui_preferences_repo = SQLiteUIPreferencesRepository(connection)
    event_log_repo = SQLiteEventLogRepository(connection)
    projects_repo = SQLiteProjectsRepository(connection)
    profiles_repo = SQLiteProfilesRepository(connection)
    agents_repo = SQLiteAgentsRepository(connection)
    analysis_repo = SQLiteAnalysisRepository(connection)
    datasets_repo = SQLiteDatasetsRepository(connection)
    experiments_repo = SQLiteExperimentsRepository(connection)
    model_versions_repo = SQLiteModelVersionsRepository(connection)
    training_repo = SQLiteTrainingRepository(connection)
    runtime_operations_repo = SQLiteRuntimeOperationsRepository(connection)
    lineage_resource_links_repo = SQLiteLineageResourceLinksRepository(connection)

    error_reporter = ApplicationErrorReporter(event_log_repo)
    runtime_operations = RuntimeOperationCoordinator(runtime_operations_repo)
    operations_center = OperationsCenterService(
        event_log=event_log_repo,
        runtime_operations=runtime_operations_repo,
    )
    lineage_runtime_safety = LineageRuntimeSafety(
        lineage_resource_links_repo,
        runtime_operations,
    )
    abandoned = runtime_operations.recover_orphaned_operations()
    if abandoned:
        error_reporter.report_message(
            f"После предыдущего завершения освобождено операций: {abandoned}",
            component="bootstrap.runtime_recovery",
            level="WARNING",
            entity_kind="runtime",
            entity_id="startup",
            context={"abandoned_operations": abandoned},
        )

    workflow_supervisor = WorkflowSupervisor()
    style_service = StylePreferencesService(ui_preferences_repo)
    docs_service = DocsService()
    projects_service = ProjectsService(projects_repo=projects_repo)
    profiles_service = ProfilesService(profiles_repo=profiles_repo)
    agents_service = AgentsService(agents_repo=agents_repo)
    analysis_service = AnalysisService(analysis_repo=analysis_repo)
    datasets_service = DatasetsService(datasets_repo=datasets_repo)
    model_versions_service = ModelVersionsService(
        model_versions_repo=model_versions_repo
    )
    local_model_service = LocalModelService(
        probe_provider=FilesystemLocalModelProbeProvider()
    )
    experiments_service = ExperimentsService(
        experiments_repo=experiments_repo,
        local_model_service=local_model_service,
        model_versions_service=model_versions_service,
        operation_coordinator=runtime_operations,
        error_reporter=error_reporter,
    )
    training_service = TrainingService(
        training_repo=training_repo,
        profiles_service=profiles_service,
        datasets_service=datasets_service,
        local_model_service=local_model_service,
        full_backend=LocalFullFineTuneBackend(paths.artifacts),
        operation_coordinator=runtime_operations,
        error_reporter=error_reporter,
    )
    automation_service = AutomationService(
        recipe_provider=FilesystemAutomationRecipeProvider(
            paths.root / "automation" / "recipes"
        ),
        operation_coordinator=runtime_operations,
        workspace_root=paths.root,
        audit_trail=AutomationAuditTrail(event_log_repo),
    )
    telemetry_service = SystemTelemetryService(
        system_provider=PsutilTelemetryProvider(),
        gpu_provider=NvidiaSmiTelemetryProvider(),
    )

    shell_vm = ShellViewModel(workflow_supervisor=workflow_supervisor)
    dashboard_vm = DashboardViewModel(
        projects_service=projects_service,
        training_service=training_service,
        model_versions_service=model_versions_service,
        datasets_service=datasets_service,
        experiments_service=experiments_service,
    )
    docs_vm = DocsViewModel(docs_service=docs_service)
    style_vm = StyleViewModel(style_service=style_service)
    datasets_vm = DatasetsViewModel(datasets_service=datasets_service)
    profiles_vm = ProfilesViewModel(profiles_service=profiles_service)
    agents_vm = AgentsViewModel(
        agents_service=agents_service,
        lineage_loader_factory=lineage_loader_factory,
        lineage_error_reporter=error_reporter,
    )
    training_vm = TrainingViewModel(
        training_service=training_service,
        model_versions_service=model_versions_service,
        local_model_service=local_model_service,
    )
    snapshots_vm = SnapshotsViewModel(
        model_versions_service=model_versions_service
    )
    tests_vm = TestsViewModel(experiments_service=experiments_service)
    analysis_vm = AnalysisViewModel(
        analysis_service=analysis_service,
        experiments_service=experiments_service,
    )
    automation_vm = AutomationViewModel(automation_service=automation_service)
    telemetry_vm = TelemetryViewModel(telemetry_service=telemetry_service)

    return AppContainer(
        settings=settings,
        shell_vm=shell_vm,
        dashboard_vm=dashboard_vm,
        docs_vm=docs_vm,
        style_vm=style_vm,
        datasets_vm=datasets_vm,
        profiles_vm=profiles_vm,
        agents_vm=agents_vm,
        training_vm=training_vm,
        snapshots_vm=snapshots_vm,
        tests_vm=tests_vm,
        analysis_vm=analysis_vm,
        automation_vm=automation_vm,
        telemetry_vm=telemetry_vm,
        runtime_operations=runtime_operations,
        lineage_loader_factory=lineage_loader_factory,
        lineage_runtime_safety=lineage_runtime_safety,
        operations_center=operations_center,
        error_reporter=error_reporter,
    )
