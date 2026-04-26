from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.application.agents.service import AgentsService
from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.projects.service import ProjectsService
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.style.service import StylePreferencesService
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.application.workflows.supervisor import WorkflowSupervisor
from persona_training_lab.config.app_settings import AppSettings
from persona_training_lab.config.paths import build_workspace_paths, ensure_workspace_dirs
from persona_training_lab.infrastructure.artifacts.manager import LocalArtifactManager
from persona_training_lab.infrastructure.logging.structured import configure_logging
from persona_training_lab.infrastructure.persistence.repositories.event_log import SQLiteEventLogRepository
from persona_training_lab.infrastructure.persistence.repositories.agents import SQLiteAgentsRepository
from persona_training_lab.infrastructure.persistence.repositories.datasets import SQLiteDatasetsRepository
from persona_training_lab.infrastructure.persistence.repositories.experiments import SQLiteExperimentsRepository
from persona_training_lab.infrastructure.persistence.repositories.projects import SQLiteProjectsRepository
from persona_training_lab.infrastructure.persistence.repositories.profiles import SQLiteProfilesRepository
from persona_training_lab.infrastructure.persistence.repositories.training import SQLiteTrainingRepository
from persona_training_lab.infrastructure.persistence.repositories.ui_preferences import (
    SQLiteUIPreferencesRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.db import SQLiteDatabase
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel
from persona_training_lab.ui.viewmodels.docs import DocsViewModel
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel
from persona_training_lab.ui.viewmodels.datasets import DatasetsViewModel
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel
from persona_training_lab.ui.viewmodels.shell import ShellViewModel
from persona_training_lab.ui.viewmodels.style import StyleViewModel
from persona_training_lab.ui.viewmodels.training import TrainingViewModel
from persona_training_lab.ui.viewmodels.snapshots import SnapshotsViewModel
from persona_training_lab.ui.viewmodels.tests import TestsViewModel
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel


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


def build_container() -> AppContainer:
    configure_logging()

    settings = AppSettings()
    paths = build_workspace_paths(settings)
    ensure_workspace_dirs(paths)

    db = SQLiteDatabase(paths.sqlite_db)
    connection = db.connect()
    create_minimal_schema(connection)

    artifact_manager = LocalArtifactManager(paths)
    artifact_manager.ensure_layout()

    ui_preferences_repo = SQLiteUIPreferencesRepository(connection)
    _event_log_repo = SQLiteEventLogRepository(connection)
    projects_repo = SQLiteProjectsRepository(connection)
    profiles_repo = SQLiteProfilesRepository(connection)
    agents_repo = SQLiteAgentsRepository(connection)
    datasets_repo = SQLiteDatasetsRepository(connection)
    experiments_repo = SQLiteExperimentsRepository(connection)
    training_repo = SQLiteTrainingRepository(connection)

    workflow_supervisor = WorkflowSupervisor()
    style_service = StylePreferencesService(ui_preferences_repo)
    docs_service = DocsService()
    projects_service = ProjectsService(projects_repo=projects_repo)
    profiles_service = ProfilesService(profiles_repo=profiles_repo)
    agents_service = AgentsService(agents_repo=agents_repo)
    datasets_service = DatasetsService(datasets_repo=datasets_repo)
    experiments_service = ExperimentsService(experiments_repo=experiments_repo)
    training_service = TrainingService(training_repo=training_repo)

    shell_vm = ShellViewModel(workflow_supervisor=workflow_supervisor)
    dashboard_vm = DashboardViewModel(docs_service=docs_service, projects_service=projects_service)
    docs_vm = DocsViewModel(docs_service=docs_service)
    style_vm = StyleViewModel(style_service=style_service)
    datasets_vm = DatasetsViewModel(datasets_service=datasets_service)
    profiles_vm = ProfilesViewModel(profiles_service=profiles_service)
    agents_vm = AgentsViewModel(agents_service=agents_service)
    training_vm = TrainingViewModel(training_service=training_service)
    snapshots_vm = SnapshotsViewModel()
    tests_vm = TestsViewModel(experiments_service=experiments_service)
    analysis_vm = AnalysisViewModel()

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
    )
