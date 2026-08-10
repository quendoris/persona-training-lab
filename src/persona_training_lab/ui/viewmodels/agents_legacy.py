from __future__ import annotations

from persona_training_lab.application.datasets.status_mapping import (
    normalize_dataset_status,
)
from persona_training_lab.application.experiments.status_mapping import (
    normalize_evaluation_status,
)
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.model_versions.status_mapping import (
    normalize_model_version_status,
)
from persona_training_lab.application.training.status_mapping import (
    normalize_training_status,
)
from persona_training_lab.domain.datasets.statuses import DatasetVersionStatus
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.domain.models.statuses import ModelVersionStatus
from persona_training_lab.domain.training.statuses import TrainingRunStatus
from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentDetailView,
    AgentText,
    PortraitStats,
    VersionNodeView,
)
from persona_training_lab.ui.viewmodels.agents_guidance import (
    AgentsGuidanceViewModel,
)


_MISSING = "—"


class AgentsViewModel(AgentsGuidanceViewModel):
    """Compatibility VM retaining the pre-atomic graph and detail projection."""

    __slots__ = ()

    def selected_detail(self) -> AgentDetailView:
        return self.node_detail("snapshot")

    def node_detail(self, node_id: str) -> AgentDetailView:
        datasets = self._datasets()
        runs = self._training_runs()
        portraits = self._portraits()
        latest_dataset = datasets[0] if datasets else None
        latest_run = runs[0] if runs else None
        latest_portrait = self._portrait_stats(portraits[0]) if portraits else None

        if node_id == "base":
            return AgentDetailView(
                UserMessage("agents.node.kind.base_model"),
                UserMessage(
                    "agents.legacy.detail.base.body",
                    {
                        "model": (
                            getattr(latest_run, "base_model", _MISSING)
                            if latest_run
                            else _MISSING
                        )
                    },
                ),
                _messages(
                    "agents.legacy.detail.base.check.files",
                    "agents.legacy.detail.base.check.compare",
                    "agents.legacy.detail.base.check.protocol",
                ),
                _messages(
                    "agents.legacy.detail.base.action.model",
                    "agents.legacy.detail.base.action.dataset",
                ),
            )
        if node_id == "dataset":
            return AgentDetailView(
                UserMessage("agents.node.kind.dataset"),
                UserMessage(
                    "agents.legacy.detail.dataset.body",
                    {
                        "title": getattr(latest_dataset, "title", _MISSING),
                        "status": _dataset_status_message(latest_dataset),
                        "records": getattr(
                            latest_dataset,
                            "record_count",
                            _MISSING,
                        ),
                        "valid": getattr(
                            latest_dataset,
                            "valid_count",
                            _MISSING,
                        ),
                        "errors": getattr(
                            latest_dataset,
                            "invalid_count",
                            _MISSING,
                        ),
                    },
                ),
                _messages(
                    "agents.legacy.detail.dataset.check.structure",
                    "agents.legacy.detail.dataset.check.approved",
                    "agents.legacy.detail.dataset.check.meaning",
                ),
                _messages(
                    "agents.legacy.detail.dataset.action.validate",
                    "agents.legacy.detail.dataset.action.approve",
                    "agents.legacy.detail.dataset.action.training",
                ),
            )
        if node_id == "training":
            return AgentDetailView(
                UserMessage("agents.node.kind.training_run"),
                UserMessage(
                    "agents.legacy.detail.training.body",
                    {
                        "run": getattr(latest_run, "run_id", _MISSING),
                        "title": getattr(latest_run, "title", _MISSING),
                        "status": _training_status_message(latest_run),
                        "epoch": getattr(
                            latest_run,
                            "epoch_progress",
                            _MISSING,
                        ),
                        "loss": getattr(latest_run, "loss", _MISSING),
                        "artifact": (
                            getattr(latest_run, "artifact_path", "")
                            or _MISSING
                        ),
                    },
                ),
                _messages(
                    "agents.legacy.detail.training.check.completed",
                    "agents.legacy.detail.training.check.artifact",
                    "agents.legacy.detail.training.check.logs",
                    "agents.legacy.detail.training.check.ui",
                ),
                _messages(
                    "agents.legacy.detail.training.action.logs",
                    "agents.legacy.detail.training.action.snapshot",
                    "agents.legacy.detail.training.action.retry",
                ),
            )
        if node_id == "snapshot":
            return AgentDetailView(
                UserMessage("agents.node.kind.model_version"),
                self._current_version_body(latest_portrait),
                _messages(
                    "agents.legacy.detail.version.check.registered",
                    "agents.legacy.detail.version.check.artifact",
                    "agents.legacy.detail.version.check.run",
                    "agents.legacy.detail.version.check.portrait",
                ),
                _messages(
                    "agents.legacy.detail.version.action.current",
                    "agents.legacy.detail.version.action.compare",
                    "agents.legacy.detail.version.action.portrait",
                    "agents.legacy.detail.version.action.failed",
                    "agents.legacy.detail.version.action.rollback",
                ),
            )
        if node_id == "portrait":
            return AgentDetailView(
                UserMessage("agents.legacy.kind.portrait"),
                UserMessage(
                    "agents.legacy.detail.portrait.body",
                    {
                        "title": (
                            latest_portrait.title
                            if latest_portrait
                            else _MISSING
                        ),
                        "passed": (
                            latest_portrait.passed if latest_portrait else 0
                        ),
                        "total": (
                            latest_portrait.total if latest_portrait else 0
                        ),
                        "errors": (
                            latest_portrait.failures
                            if latest_portrait
                            else _MISSING
                        ),
                        "scores": (
                            self._score_line(latest_portrait.scores)
                            if latest_portrait
                            else _MISSING
                        ),
                    },
                ),
                _messages(
                    "agents.legacy.detail.portrait.check.valid",
                    "agents.legacy.detail.portrait.check.kpi",
                    "agents.legacy.detail.portrait.check.protocol",
                ),
                _messages(
                    "agents.legacy.detail.portrait.action.retry",
                    "agents.legacy.detail.portrait.action.analysis",
                    "agents.legacy.detail.portrait.action.export",
                ),
            )
        if node_id == "delta":
            delta: AgentText = self.delta_line() or UserMessage(
                "agents.legacy.guidance.delta_required"
            )
            return AgentDetailView(
                UserMessage("agents.node.kind.analysis_delta"),
                UserMessage(
                    "agents.legacy.detail.delta.body",
                    {
                        "delta": delta,
                        "latest": (
                            getattr(portraits[0], "title", _MISSING)
                            if portraits
                            else _MISSING
                        ),
                        "previous": (
                            getattr(portraits[1], "title", _MISSING)
                            if len(portraits) > 1
                            else _MISSING
                        ),
                    },
                ),
                _messages(
                    "agents.legacy.detail.delta.check.two",
                    "agents.legacy.detail.delta.check.battery",
                    "agents.legacy.detail.delta.check.scoring",
                    "agents.legacy.detail.delta.check.order",
                ),
                _messages(
                    "agents.legacy.detail.delta.action.analysis",
                    "agents.legacy.detail.delta.action.portrait",
                    "agents.legacy.detail.delta.action.note",
                ),
            )
        return self.node_detail("snapshot")

    def _current_version_body(self, latest: PortraitStats | None) -> UserMessage:
        versions = self._model_versions()
        version = versions[0] if versions else None
        if version is None:
            return UserMessage("agents.legacy.detail.version.empty")
        score_line: AgentText = (
            self._score_line(latest.scores)
            if latest
            else UserMessage("agents.legacy.value.portrait_missing")
        )
        delta: AgentText = self.delta_line() or UserMessage(
            "agents.legacy.guidance.delta_required"
        )
        return UserMessage(
            "agents.legacy.detail.version.body",
            {
                "title": getattr(version, "title", _MISSING),
                "status": _version_status_message(version),
                "artifact": getattr(version, "artifact_path", "") or _MISSING,
                "scores": score_line,
                "delta": delta,
            },
        )

    def version_nodes(self) -> tuple[VersionNodeView, ...]:
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
            VersionNodeView(
                "base",
                0,
                UserMessage(
                    "agents.node.title.base_model",
                    {
                        "label": (
                            getattr(latest_run, "base_model", _MISSING)
                            if latest_run
                            else _MISSING
                        )
                    },
                ),
                UserMessage("agents.legacy.node.base.subtitle"),
                UserMessage("agents.status.source"),
                "good" if latest_run else "pending",
                "main",
            ),
            VersionNodeView(
                "dataset",
                1,
                UserMessage(
                    "agents.node.title.dataset",
                    {
                        "label": (
                            getattr(latest_run, "dataset_version", "")
                            or getattr(latest_dataset, "title", _MISSING)
                        )
                    },
                ),
                self._dataset_note_message(),
                _dataset_status_message(latest_dataset),
                (
                    "good"
                    if latest_dataset
                    and normalize_dataset_status(
                        getattr(latest_dataset, "status", "")
                    )
                    is DatasetVersionStatus.APPROVED
                    else "pending"
                ),
                "main",
            ),
            VersionNodeView(
                "training",
                2,
                UserMessage(
                    "agents.node.title.training_run",
                    {"label": getattr(latest_run, "run_id", _MISSING)},
                ),
                (
                    UserMessage(
                        "agents.legacy.node.entity_title",
                        {"title": getattr(latest_run, "title", _MISSING)},
                    )
                    if latest_run
                    else UserMessage("agents.legacy.node.training.empty")
                ),
                _training_status_message(latest_run),
                (
                    "good"
                    if latest_run and getattr(latest_run, "artifact_path", "")
                    else "pending"
                ),
                "main",
            ),
            VersionNodeView(
                "snapshot",
                3,
                UserMessage(
                    "agents.node.title.model_version",
                    {"label": getattr(latest_version, "version_id", _MISSING)},
                ),
                (
                    UserMessage(
                        "agents.legacy.node.entity_title",
                        {"title": getattr(latest_version, "title", _MISSING)},
                    )
                    if latest_version
                    else UserMessage("agents.legacy.node.version.empty")
                ),
                _version_status_message(latest_version),
                "good" if latest_version else "pending",
                "current",
            ),
            VersionNodeView(
                "portrait",
                4,
                UserMessage(
                    "agents.node.title.evaluation_run",
                    {
                        "label": (
                            latest_portrait.title
                            if latest_portrait
                            else _MISSING
                        )
                    },
                ),
                self._portrait_note_message(latest_portrait),
                (
                    UserMessage("agents.status.good")
                    if latest_portrait and latest_portrait.failures == 0
                    else UserMessage("agents.status.pending")
                ),
                (
                    "good"
                    if latest_portrait and latest_portrait.failures == 0
                    else "pending"
                ),
                "main",
            ),
            VersionNodeView(
                "delta",
                5,
                UserMessage("agents.node.delta.title"),
                (
                    UserMessage(
                        "agents.legacy.node.delta.ready",
                        {"delta": self.delta_line()},
                    )
                    if self.delta_line()
                    else UserMessage("agents.legacy.node.delta.pending")
                ),
                (
                    UserMessage("agents.status.good")
                    if len(portraits) >= 2
                    else UserMessage("agents.status.pending")
                ),
                "good" if len(portraits) >= 2 else "pending",
                "main",
            ),
        )

    def _portrait_note_message(self, latest: PortraitStats | None) -> UserMessage:
        if latest is None:
            return UserMessage("agents.legacy.portrait.none")
        score_line = self._score_line(latest.scores)
        return UserMessage(
            "agents.legacy.portrait.summary",
            {
                "passed": latest.passed,
                "total": latest.total,
                "failures": latest.failures,
                "scores": (
                    score_line
                    if score_line
                    else UserMessage("agents.legacy.value.no_score")
                ),
            },
        )

    def _portrait_note(self, latest: PortraitStats | None) -> str:
        from persona_training_lab.ui.i18n.text import render_user_message

        return render_user_message(None, self._portrait_note_message(latest))


def _messages(*keys: str) -> tuple[UserMessage, ...]:
    return tuple(UserMessage(key) for key in keys)


def _dataset_status_message(dataset: object | None) -> UserMessage:
    status = normalize_dataset_status(getattr(dataset, "status", ""))
    key = {
        DatasetVersionStatus.DRAFT: "draft",
        DatasetVersionStatus.IMPORTED: "imported",
        DatasetVersionStatus.VALIDATED: "validated",
        DatasetVersionStatus.APPROVED: "approved",
        DatasetVersionStatus.ARCHIVED: "archived",
        DatasetVersionStatus.UNKNOWN: "unknown",
    }[status]
    return UserMessage(f"agents.legacy.status.dataset.{key}")


def _training_status_message(run: object | None) -> UserMessage:
    status = normalize_training_status(getattr(run, "status", ""))
    key = {
        TrainingRunStatus.CREATED: "created",
        TrainingRunStatus.READY: "ready",
        TrainingRunStatus.RUNNING: "running",
        TrainingRunStatus.FAILED: "failed",
        TrainingRunStatus.COMPLETED: "completed",
        TrainingRunStatus.UNKNOWN: "unknown",
    }[status]
    return UserMessage(f"agents.legacy.status.training.{key}")


def _version_status_message(version: object | None) -> UserMessage:
    status = normalize_model_version_status(getattr(version, "status", ""))
    key = {
        ModelVersionStatus.DRAFT: "draft",
        ModelVersionStatus.READY: "ready",
        ModelVersionStatus.ARCHIVED: "archived",
        ModelVersionStatus.FAILED: "failed",
        ModelVersionStatus.UNKNOWN: "unknown",
    }[status]
    return UserMessage(f"agents.legacy.status.version.{key}")


def _portrait_status_message(experiment: object | None) -> UserMessage:
    status = normalize_evaluation_status(getattr(experiment, "status", ""))
    key = {
        EvaluationRunStatus.CREATED: "created",
        EvaluationRunStatus.RUNNING: "running",
        EvaluationRunStatus.PARTIAL: "partial",
        EvaluationRunStatus.FAILED: "failed",
        EvaluationRunStatus.COMPLETED: "completed",
        EvaluationRunStatus.UNKNOWN: "unknown",
    }[status]
    return UserMessage(f"agents.legacy.status.portrait.{key}")


__all__ = ("AgentsViewModel",)
