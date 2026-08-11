from __future__ import annotations

from dataclasses import dataclass, field
import re
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.projects.service import ProjectsService
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.ui.viewmodels.experiment_semantics import (
    experiment_title_semantic,
)


SCORE_RE = re.compile(r"\bSCORE\s*:\s*([1-5])\b", re.IGNORECASE)
CASE_HEADER_RE = re.compile(r"(?m)^CASE\s+\d+")
TRAIT_ORDER = (
    "Extraversion",
    "Agreeableness",
    "Conscientiousness",
    "Emotional Stability",
    "Openness",
)
TRAIT_LABELS = {
    "Extraversion": "E",
    "Agreeableness": "A",
    "Conscientiousness": "C",
    "Emotional Stability": "S",
    "Openness": "O",
}

_STATUS_ALIASES = {
    "одобрен для обучения": "approved",
    "approved for training": "approved",
    "завершён": "completed",
    "завершен": "completed",
    "completed": "completed",
    "готово": "ready",
    "готова": "ready",
    "готов": "ready",
    "ready": "ready",
    "выполняется": "running",
    "запущено": "running",
    "running": "running",
    "черновик": "draft",
    "draft": "draft",
    "отменено": "cancelled",
    "отменён": "cancelled",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "ошибка": "error",
    "failed": "error",
    "error": "error",
    "портрет собран": "portrait_built",
    "portrait built": "portrait_built",
}
_STATUS_KEYS = {
    "approved": "dashboard.status.approved",
    "completed": "dashboard.status.completed",
    "ready": "dashboard.status.ready",
    "running": "dashboard.status.running",
    "draft": "dashboard.status.draft",
    "cancelled": "dashboard.status.cancelled",
    "error": "dashboard.status.error",
    "portrait_built": "dashboard.status.portrait_built",
}


@dataclass(frozen=True, slots=True)
class DashboardText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


DashboardTextValue = str | DashboardText


@dataclass(frozen=True, slots=True)
class DashboardRoute:
    screen: str
    focus_key: str = ""


@dataclass(frozen=True, slots=True)
class DashboardStat:
    label_key: str
    value: DashboardText
    note: DashboardText


@dataclass(frozen=True, slots=True)
class DashboardAction:
    icon: str
    title: DashboardText
    description: DashboardText
    route: DashboardRoute


@dataclass(frozen=True, slots=True)
class DashboardActivity:
    kind_key: str
    title: DashboardTextValue
    detail: DashboardText
    route: DashboardRoute
    state_key: str
    empty_title: DashboardText | None = None


@dataclass(frozen=True, slots=True)
class DashboardMetric:
    label_key: str
    value: int
    note: DashboardText


@dataclass(frozen=True, slots=True)
class DashboardAttention:
    title_key: str
    body: DashboardText


@dataclass(frozen=True, slots=True)
class DashboardLineage:
    label_key: str
    value: DashboardTextValue
    route: DashboardRoute


@dataclass(frozen=True, slots=True)
class DashboardStep:
    message: DashboardText
    route: DashboardRoute


@dataclass(slots=True, frozen=True)
class PortraitDashboardStats:
    title: DashboardTextValue
    status: str
    passed: int
    total: int
    failures: int
    scores: dict[str, float]


def dashboard_text(key: str, **values: object) -> DashboardText:
    return DashboardText(key, MappingProxyType(dict(values)))


def _dashboard_experiment_title(experiment: object) -> DashboardTextValue:
    semantic = experiment_title_semantic(experiment)
    if semantic.key:
        return dashboard_text(semantic.key, **dict(semantic.values))
    return semantic.raw


@dataclass(slots=True)
class DashboardViewModel:
    docs_service: DocsService
    projects_service: ProjectsService
    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
    datasets_service: DatasetsService | None = None
    experiments_service: ExperimentsService | None = None

    def quick_actions(self) -> tuple[DashboardAction, ...]:
        next_step = self.next_best_step()
        return (
            DashboardAction(
                "1",
                dashboard_text("dashboard.action.next.title"),
                next_step.message,
                next_step.route,
            ),
            DashboardAction(
                "2",
                dashboard_text("dashboard.action.portrait.title"),
                dashboard_text("dashboard.action.portrait.description"),
                DashboardRoute("tests", "focus.tests.build_portrait"),
            ),
            DashboardAction(
                "3",
                dashboard_text("dashboard.action.analysis.title"),
                dashboard_text("dashboard.action.analysis.description"),
                DashboardRoute("analysis"),
            ),
        )

    def quick_start(self) -> list[str]:
        return self.docs_service.get_quick_start_items()

    def stats(self) -> tuple[DashboardStat, ...]:
        if not self._has_live_workflow_services():
            return self._project_stats()

        training_runs = self._training_runs()
        versions = self._model_versions()
        datasets = self._datasets()
        latest_portrait = self._latest_portrait()
        latest_training = training_runs[0] if training_runs else None
        latest_version = versions[0] if versions else None

        training_value = (
            self._status_text(getattr(latest_training, "status", ""))
            if latest_training is not None
            else dashboard_text("dashboard.raw", value="—")
        )
        training_note = (
            dashboard_text("dashboard.raw", value=latest_training.title)
            if latest_training is not None
            else dashboard_text("dashboard.note.no_training_run")
        )
        version_note = (
            dashboard_text("dashboard.raw", value=latest_version.title)
            if latest_version is not None
            else dashboard_text("dashboard.note.no_snapshots")
        )
        portrait_value = (
            dashboard_text(
                "dashboard.raw",
                value=self._score_line(latest_portrait.scores),
            )
            if latest_portrait and latest_portrait.scores
            else dashboard_text("dashboard.raw", value="—")
        )

        return (
            DashboardStat(
                "dashboard.stat.training",
                training_value,
                training_note,
            ),
            DashboardStat(
                "dashboard.stat.snapshots",
                dashboard_text("dashboard.raw", value=f"{len(versions):02d}"),
                version_note,
            ),
            DashboardStat(
                "dashboard.stat.datasets",
                dashboard_text("dashboard.raw", value=f"{len(datasets):02d}"),
                self._dataset_note(datasets),
            ),
            DashboardStat(
                "dashboard.stat.portrait",
                portrait_value,
                self._portrait_note(latest_portrait),
            ),
        )

    def recent_activity(self) -> tuple[DashboardActivity, ...]:
        rows: list[DashboardActivity] = []
        training_runs = self._training_runs()
        versions = self._model_versions()
        datasets = self._datasets()
        portraits = self._portraits()

        if training_runs:
            run = training_runs[0]
            status = getattr(run, "status", "")
            artifact = getattr(run, "artifact_path", "") or "—"
            rows.append(
                DashboardActivity(
                    "dashboard.kind.training",
                    run.title,
                    dashboard_text(
                        "dashboard.activity.training",
                        status=self._status_text(status),
                        artifact=artifact,
                    ),
                    DashboardRoute("training"),
                    self._activity_state(
                        status,
                        ready=bool(artifact and artifact != "—"),
                    ),
                )
            )
        if versions:
            version = versions[0]
            status = getattr(version, "status", "")
            detail = (
                getattr(version, "quality_summary", "")
                or getattr(version, "artifact_path", "")
                or "—"
            )
            rows.append(
                DashboardActivity(
                    "dashboard.kind.snapshot",
                    version.title,
                    dashboard_text(
                        "dashboard.activity.snapshot",
                        status=self._status_text(status),
                        detail=detail,
                    ),
                    DashboardRoute("snapshots"),
                    self._activity_state(status, ready=True),
                )
            )
        if portraits:
            portrait = self._portrait_stats(portraits[0])
            rows.append(
                DashboardActivity(
                    "dashboard.kind.portrait",
                    portrait.title,
                    self._portrait_note(portrait),
                    DashboardRoute("tests", "focus.tests.build_portrait"),
                    (
                        "dashboard.state.attention"
                        if portrait.failures
                        else "dashboard.state.ready"
                    ),
                )
            )
        if datasets:
            dataset = datasets[0]
            status = getattr(dataset, "status", "")
            invalid = int(getattr(dataset, "invalid_count", 0) or 0)
            rows.append(
                DashboardActivity(
                    "dashboard.kind.dataset",
                    dataset.title,
                    dashboard_text(
                        "dashboard.activity.dataset",
                        status=self._status_text(status),
                        valid=getattr(dataset, "valid_count", 0),
                        total=getattr(dataset, "record_count", 0),
                    ),
                    DashboardRoute("datasets", "focus.datasets.validate"),
                    (
                        "dashboard.state.attention"
                        if invalid
                        else self._activity_state(
                            status,
                            ready=self._is_dataset_approved(dataset),
                        )
                    ),
                )
            )
        if not rows:
            projects = self._projects()
            if projects:
                latest = projects[0]
                rows.append(
                    DashboardActivity(
                        "dashboard.kind.project",
                        latest.title,
                        self._status_text(getattr(latest, "status", "")),
                        DashboardRoute("dashboard"),
                        self._activity_state(getattr(latest, "status", "")),
                    )
                )

        if rows:
            return tuple(rows[:4])
        return (
            DashboardActivity(
                "",
                "",
                dashboard_text("dashboard.activity.empty.description"),
                DashboardRoute("datasets", "focus.datasets.add"),
                "dashboard.state.waiting",
                empty_title=dashboard_text("dashboard.activity.empty.title"),
            ),
        )

    def system_metrics(self) -> tuple[DashboardMetric, ...]:
        training_runs = self._training_runs()
        datasets = self._datasets()
        latest_portrait = self._latest_portrait()
        versions = self._model_versions()
        training_progress = self._progress_value(
            training_runs[0].progress if training_runs else "0"
        )
        dataset_ready = self._dataset_readiness(datasets)
        portrait_ready = self._portrait_readiness(latest_portrait)
        artifact_ready = 100 if versions else 0
        return (
            DashboardMetric(
                "dashboard.metric.training",
                training_progress,
                self._progress_note(training_runs),
            ),
            DashboardMetric(
                "dashboard.metric.dataset",
                dataset_ready,
                self._dataset_note(datasets),
            ),
            DashboardMetric(
                "dashboard.metric.portrait",
                portrait_ready,
                self._portrait_note(latest_portrait),
            ),
            DashboardMetric(
                "dashboard.metric.snapshot",
                artifact_ready,
                dashboard_text(
                    "dashboard.note.snapshot_registered"
                    if versions
                    else "dashboard.note.snapshot_missing"
                ),
            ),
        )

    def attention_items(self) -> tuple[DashboardAttention, ...]:
        latest_portrait = self._latest_portrait()
        portraits = self._portraits()
        items = [
            DashboardAttention(
                "dashboard.attention.next",
                self.next_best_step().message,
            )
        ]
        if latest_portrait is not None:
            items.append(
                DashboardAttention(
                    "dashboard.attention.portrait",
                    self._portrait_note(latest_portrait),
                )
            )
        if len(portraits) >= 2:
            latest = self._portrait_stats(portraits[0])
            previous = self._portrait_stats(portraits[1])
            delta = self._delta_line(previous.scores, latest.scores)
            items.append(
                DashboardAttention(
                    "dashboard.attention.delta",
                    (
                        dashboard_text("dashboard.raw", value=delta)
                        if delta
                        else dashboard_text("dashboard.note.no_common_traits")
                    ),
                )
            )
        else:
            items.append(
                DashboardAttention(
                    "dashboard.attention.delta",
                    dashboard_text("dashboard.note.second_portrait_required"),
                )
            )
        items.append(
            DashboardAttention(
                "dashboard.attention.documentation",
                dashboard_text("dashboard.note.experiment_protocol"),
            )
        )
        return tuple(items[:4])

    def quick_lineage(self) -> tuple[DashboardLineage, ...]:
        training_runs = self._training_runs()
        versions = self._model_versions()
        datasets = self._datasets()
        portraits = self._portraits()
        latest_run = training_runs[0] if training_runs else None
        latest_version = versions[0] if versions else None
        latest_dataset = datasets[0] if datasets else None
        latest_portrait = (
            self._portrait_stats(portraits[0]) if portraits else None
        )
        return (
            DashboardLineage(
                "dashboard.lineage.base_model",
                latest_run.base_model if latest_run else "—",
                DashboardRoute("agents"),
            ),
            DashboardLineage(
                "dashboard.lineage.dataset",
                (
                    latest_run.dataset_version
                    if latest_run
                    else (latest_dataset.title if latest_dataset else "—")
                ),
                DashboardRoute("datasets"),
            ),
            DashboardLineage(
                "dashboard.lineage.training",
                latest_run.run_id if latest_run else "—",
                DashboardRoute("training"),
            ),
            DashboardLineage(
                "dashboard.lineage.snapshot",
                latest_version.version_id if latest_version else "—",
                DashboardRoute("snapshots"),
            ),
            DashboardLineage(
                "dashboard.lineage.portrait",
                latest_portrait.title if latest_portrait else "—",
                DashboardRoute("tests"),
            ),
        )

    def next_best_step(self) -> DashboardStep:
        datasets = self._datasets()
        training_runs = self._training_runs()
        versions = self._model_versions()
        portraits = self._portraits()
        latest_portrait = (
            self._portrait_stats(portraits[0]) if portraits else None
        )
        if not self._has_live_workflow_services():
            return DashboardStep(
                dashboard_text("dashboard.step.connect_services"),
                DashboardRoute("docs"),
            )
        if not datasets:
            return DashboardStep(
                dashboard_text("dashboard.step.add_dataset"),
                DashboardRoute("datasets", "focus.datasets.add"),
            )
        if not any(self._is_dataset_approved(item) for item in datasets):
            return DashboardStep(
                dashboard_text("dashboard.step.approve_dataset"),
                DashboardRoute("datasets", "focus.datasets.validate"),
            )
        if not training_runs:
            return DashboardStep(
                dashboard_text("dashboard.step.create_training"),
                DashboardRoute("training", "focus.training.create_run"),
            )
        if (
            not self._training_finished(training_runs[0])
            and not getattr(training_runs[0], "artifact_path", "")
        ):
            return DashboardStep(
                dashboard_text("dashboard.step.finish_training"),
                DashboardRoute("training", "focus.training.start"),
            )
        if not versions:
            return DashboardStep(
                dashboard_text("dashboard.step.register_snapshot"),
                DashboardRoute("snapshots", "focus.snapshots.refresh"),
            )
        if latest_portrait is None:
            return DashboardStep(
                dashboard_text("dashboard.step.collect_portrait"),
                DashboardRoute("tests", "focus.tests.build_portrait"),
            )
        if latest_portrait.failures > 0:
            return DashboardStep(
                dashboard_text("dashboard.step.repair_portrait"),
                DashboardRoute("tests", "focus.tests.build_portrait"),
            )
        if len(portraits) < 2:
            return DashboardStep(
                dashboard_text("dashboard.step.collect_second_portrait"),
                DashboardRoute("training", "focus.training.start"),
            )
        return DashboardStep(
            dashboard_text("dashboard.step.open_analysis"),
            DashboardRoute("analysis"),
        )

    def _has_live_workflow_services(self) -> bool:
        return any(
            service is not None
            for service in (
                self.training_service,
                self.model_versions_service,
                self.datasets_service,
                self.experiments_service,
            )
        )

    def _projects(self) -> list[object]:
        try:
            return self.projects_service.list_projects()
        except Exception:
            return []

    def _project_stats(self) -> tuple[DashboardStat, ...]:
        try:
            projects = self.projects_service.list_projects()
        except Exception:
            return (
                DashboardStat(
                    "dashboard.stat.projects",
                    dashboard_text("dashboard.raw", value="—"),
                    dashboard_text("dashboard.note.project_load_failed"),
                ),
            )
        if not projects:
            return (
                DashboardStat(
                    "dashboard.stat.projects",
                    dashboard_text("dashboard.raw", value="00"),
                    dashboard_text("dashboard.note.no_projects"),
                ),
            )
        latest = projects[0]
        return (
            DashboardStat(
                "dashboard.stat.projects",
                dashboard_text("dashboard.raw", value=f"{len(projects):02d}"),
                dashboard_text(
                    "dashboard.note.project_summary",
                    title=latest.title,
                    status=self._status_text(getattr(latest, "status", "")),
                ),
            ),
        )

    def _training_runs(self) -> list[object]:
        if self.training_service is None:
            return []
        try:
            return self.training_service.list_training_runs()
        except Exception:
            return []

    def _model_versions(self) -> list[object]:
        if self.model_versions_service is None:
            return []
        try:
            return self.model_versions_service.list_model_versions()
        except Exception:
            return []

    def _datasets(self) -> list[object]:
        if self.datasets_service is None:
            return []
        try:
            return self.datasets_service.list_datasets()
        except Exception:
            return []

    def _portraits(self) -> list[object]:
        if self.experiments_service is None:
            return []
        try:
            return self.experiments_service.list_experiments()
        except Exception:
            return []

    def _latest_portrait(self) -> PortraitDashboardStats | None:
        portraits = self._portraits()
        return self._portrait_stats(portraits[0]) if portraits else None

    def _portrait_stats(self, experiment: object) -> PortraitDashboardStats:
        subtitle = getattr(experiment, "subtitle", "")
        status = getattr(experiment, "status", "")
        passed, total = self._parse_passed_total(subtitle)
        values, invalid = self._parse_scores(subtitle)
        failures = max(invalid, max(0, total - passed)) if total else invalid
        return PortraitDashboardStats(
            title=_dashboard_experiment_title(experiment),
            status=status,
            passed=passed,
            total=total,
            failures=failures,
            scores={
                trait: round(sum(items) / len(items), 2)
                for trait, items in values.items()
                if items
            },
        )

    def _parse_scores(
        self,
        subtitle: str,
    ) -> tuple[dict[str, list[float]], int]:
        values: dict[str, list[float]] = {}
        invalid = 0
        for block in self._split_case_records(subtitle):
            lines = [
                line.strip()
                for line in block.splitlines()
                if line.strip()
            ]
            trait = self._field(lines, "TRAIT")
            reverse = self._field(lines, "REVERSE") == "1"
            valid_score = self._field(lines, "VALID_SCORE")
            response = self._field(lines, "RESPONSE")
            score = self._score_from_response(response)
            if score is None or valid_score == "0":
                invalid += 1
                continue
            final_score = 6 - score if reverse else score
            if trait:
                values.setdefault(trait, []).append(float(final_score))
        return values, invalid

    def _split_case_records(self, subtitle: str) -> list[str]:
        match = CASE_HEADER_RE.search(subtitle)
        if match is None:
            return []
        records = [
            record.strip()
            for record in CASE_HEADER_RE.split(subtitle[match.start() :])
            if record.strip()
        ]
        headers = CASE_HEADER_RE.findall(subtitle[match.start() :])
        return [
            f"{header}\n{record}"
            for header, record in zip(headers, records, strict=False)
        ]

    def _field(self, lines: list[str], name: str) -> str:
        prefix = f"{name}: "
        return next(
            (
                line.removeprefix(prefix).strip()
                for line in lines
                if line.startswith(prefix)
            ),
            "",
        )

    def _score_from_response(self, response: str) -> int | None:
        match = SCORE_RE.search(response)
        return int(match.group(1)) if match else None

    def _parse_passed_total(self, subtitle: str) -> tuple[int, int]:
        summary = subtitle.split("CASE ", 1)[0]
        marker = (
            summary.replace("PORTRAIT:", "")
            .replace("SUMMARY:", "")
            .strip()
            .split(" ")[0]
        )
        if "/" not in marker:
            return 0, 0
        left, right = marker.split("/", 1)
        try:
            return int(left), int(right)
        except ValueError:
            return 0, 0

    def _score_line(self, scores: dict[str, float]) -> str:
        return " · ".join(
            f"{TRAIT_LABELS[key]}={scores[key]:.2f}"
            for key in TRAIT_ORDER
            if key in scores
        )

    def _delta_line(
        self,
        previous: dict[str, float],
        latest: dict[str, float],
    ) -> str:
        parts = []
        for key in TRAIT_ORDER:
            if key in previous and key in latest:
                parts.append(
                    f"{TRAIT_LABELS[key]}={latest[key] - previous[key]:+.2f}"
                )
        return " · ".join(parts)

    def _dataset_note(self, datasets: list[object]) -> DashboardText:
        if not datasets:
            return dashboard_text("dashboard.note.no_datasets")
        approved = sum(
            1 for item in datasets if self._is_dataset_approved(item)
        )
        errors = sum(
            1
            for item in datasets
            if int(getattr(item, "invalid_count", 0) or 0) > 0
        )
        return dashboard_text(
            "dashboard.note.dataset_summary",
            approved=approved,
            errors=errors,
        )

    def _dataset_readiness(self, datasets: list[object]) -> int:
        if not datasets:
            return 0
        approved = sum(
            1 for item in datasets if self._is_dataset_approved(item)
        )
        return min(100, round(approved / len(datasets) * 100))

    def _portrait_note(
        self,
        portrait: PortraitDashboardStats | None,
    ) -> DashboardText:
        if portrait is None:
            return dashboard_text("dashboard.note.portrait_missing")
        return dashboard_text(
            "dashboard.note.portrait_summary",
            status=self._status_text(portrait.status),
            passed=portrait.passed,
            total=portrait.total,
            failures=portrait.failures,
        )

    def _portrait_readiness(
        self,
        portrait: PortraitDashboardStats | None,
    ) -> int:
        if portrait is None or portrait.total <= 0:
            return 0
        return min(100, round(portrait.passed / portrait.total * 100))

    def _progress_value(self, value: str) -> int:
        try:
            return max(0, min(100, int(float(value))))
        except (TypeError, ValueError):
            return 0

    def _progress_note(self, runs: list[object]) -> DashboardText:
        if not runs:
            return dashboard_text("dashboard.note.no_training_run")
        run = runs[0]
        return dashboard_text(
            "dashboard.note.progress_summary",
            status=self._status_text(getattr(run, "status", "")),
            epoch=getattr(run, "epoch_progress", "—"),
            loss=getattr(run, "loss", "—"),
        )

    @staticmethod
    def _status_code(status: object) -> str:
        return _STATUS_ALIASES.get(str(status).strip().casefold(), "")

    def _status_text(self, status: object) -> DashboardText:
        code = self._status_code(status)
        key = _STATUS_KEYS.get(code)
        if key is not None:
            return dashboard_text(key)
        value = str(status).strip() or "—"
        return dashboard_text("dashboard.raw", value=value)

    def _activity_state(
        self,
        status: object,
        *,
        ready: bool = False,
    ) -> str:
        code = self._status_code(status)
        if code == "error":
            return "dashboard.state.attention"
        if code in {"draft", "cancelled"}:
            return "dashboard.state.waiting"
        if code in {"completed", "ready", "portrait_built", "approved"}:
            return "dashboard.state.ready"
        if ready:
            return "dashboard.state.ready"
        return "dashboard.state.present"

    def _is_dataset_approved(self, dataset: object) -> bool:
        return self._status_code(getattr(dataset, "status", "")) == "approved"

    def _training_finished(self, run: object) -> bool:
        return self._status_code(getattr(run, "status", "")) in {
            "completed",
            "ready",
        }
