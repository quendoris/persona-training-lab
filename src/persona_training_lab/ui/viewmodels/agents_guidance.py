from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.datasets.status_mapping import (
    normalize_dataset_status,
)
from persona_training_lab.application.experiments.portrait import parse_portrait_payload
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.application.training.status_mapping import (
    normalize_training_status,
)
from persona_training_lab.domain.datasets.statuses import DatasetVersionStatus
from persona_training_lab.domain.training.statuses import TrainingRunStatus
from persona_training_lab.ui.i18n.text import render_user_message
from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentRoleView,
    AgentText,
    PortraitStats,
)
from persona_training_lab.ui.viewmodels.agents_overview import AgentsOverviewViewModel


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


@dataclass(slots=True)
class AgentsGuidanceViewModel(AgentsOverviewViewModel):
    """Compatibility guidance over direct service read models."""

    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
    datasets_service: DatasetsService | None = None
    experiments_service: ExperimentsService | None = None

    def roles(self) -> tuple[AgentRoleView, ...]:
        next_step = self.next_best_step_message()
        latest = self._latest_portrait()
        delta: AgentText = self.delta_line() or UserMessage(
            "agents.legacy.guidance.delta_required"
        )
        dataset_note = self._dataset_note_message()
        return (
            AgentRoleView(
                "version_navigator",
                UserMessage("agents.legacy.role.navigator.title"),
                UserMessage("agents.legacy.role.navigator.mission"),
                next_step,
                UserMessage("agents.legacy.role.navigator.status"),
            ),
            AgentRoleView(
                "researcher",
                UserMessage("agents.legacy.role.researcher.title"),
                UserMessage("agents.legacy.role.researcher.mission"),
                UserMessage(
                    "agents.legacy.role.researcher.next",
                    {"delta": delta},
                ),
                UserMessage("agents.legacy.role.researcher.status"),
            ),
            AgentRoleView(
                "dataset_auditor",
                UserMessage("agents.legacy.role.dataset.title"),
                UserMessage("agents.legacy.role.dataset.mission"),
                dataset_note,
                UserMessage("agents.legacy.role.dataset.status"),
            ),
            AgentRoleView(
                "protocolist",
                UserMessage("agents.legacy.role.protocol.title"),
                UserMessage("agents.legacy.role.protocol.mission"),
                UserMessage("agents.legacy.role.protocol.next"),
                UserMessage("agents.legacy.role.protocol.status"),
            ),
            AgentRoleView(
                "labeler",
                UserMessage("agents.legacy.role.labeler.title"),
                UserMessage("agents.legacy.role.labeler.mission"),
                self._labeler_step_message(latest),
                UserMessage("agents.legacy.role.labeler.status"),
            ),
        )

    def next_best_step_message(self) -> UserMessage:
        datasets = self._datasets()
        runs = self._training_runs()
        versions = self._model_versions()
        portraits = self._portraits()
        latest = self._portrait_stats(portraits[0]) if portraits else None
        if not datasets:
            return UserMessage("agents.legacy.next.dataset_add")
        if not any(
            normalize_dataset_status(getattr(item, "status", ""))
            is DatasetVersionStatus.APPROVED
            for item in datasets
        ):
            return UserMessage("agents.legacy.next.dataset_approve")
        if not runs:
            return UserMessage("agents.legacy.next.training_create")
        if (
            not getattr(runs[0], "artifact_path", "")
            and normalize_training_status(getattr(runs[0], "status", ""))
            is not TrainingRunStatus.COMPLETED
        ):
            return UserMessage("agents.legacy.next.training_complete")
        if not versions:
            return UserMessage("agents.legacy.next.version_create")
        if latest is None:
            return UserMessage("agents.legacy.next.portrait_build")
        if latest.failures > 0:
            return UserMessage("agents.legacy.next.portrait_retry")
        if len(portraits) < 2:
            return UserMessage("agents.legacy.next.delta_second")
        return UserMessage("agents.legacy.next.analysis_open")

    def next_best_step(self) -> str:
        """Base-locale compatibility surface for historical callers."""

        return render_user_message(None, self.next_best_step_message())

    def delta_line(self) -> str:
        portraits = self._portraits()
        if len(portraits) < 2:
            return ""
        latest = self._portrait_stats(portraits[0])
        previous = self._portrait_stats(portraits[1])
        parts = []
        for key in TRAIT_ORDER:
            if key in latest.scores and key in previous.scores:
                parts.append(
                    f"{TRAIT_LABELS[key]}="
                    f"{latest.scores[key] - previous.scores[key]:+.2f}"
                )
        return " · ".join(parts)

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

    def _latest_portrait(self) -> PortraitStats | None:
        portraits = self._portraits()
        return self._portrait_stats(portraits[0]) if portraits else None

    def _portrait_stats(self, experiment: object) -> PortraitStats:
        portrait = parse_portrait_payload(getattr(experiment, "subtitle", ""))
        invalid = sum(
            1
            for case in portrait.cases
            if case.score is None or not case.valid_score
        )
        failures = (
            max(invalid, max(0, portrait.total - portrait.passed))
            if portrait.total
            else invalid
        )
        return PortraitStats(
            title=getattr(experiment, "title", ""),
            passed=portrait.passed,
            total=portrait.total,
            failures=failures,
            scores=portrait.trait_scores(),
        )

    def _score_line(self, scores: dict[str, float]) -> str:
        return " · ".join(
            f"{TRAIT_LABELS[key]}={scores[key]:.2f}"
            for key in TRAIT_ORDER
            if key in scores
        )

    def _dataset_note_message(self) -> UserMessage:
        datasets = self._datasets()
        if not datasets:
            return UserMessage("agents.legacy.dataset.none")
        approved = sum(
            1
            for item in datasets
            if normalize_dataset_status(getattr(item, "status", ""))
            is DatasetVersionStatus.APPROVED
        )
        errors = sum(
            1
            for item in datasets
            if getattr(item, "invalid_count", 0) > 0
        )
        return UserMessage(
            "agents.legacy.dataset.summary",
            {
                "count": len(datasets),
                "approved": approved,
                "errors": errors,
            },
        )

    def _dataset_note(self) -> str:
        """Base-locale compatibility surface for historical callers."""

        return render_user_message(None, self._dataset_note_message())

    def _labeler_step_message(self, latest: PortraitStats | None) -> UserMessage:
        if latest is None:
            return UserMessage("agents.legacy.labeler.no_portrait")
        if latest.failures > 0:
            return UserMessage("agents.legacy.labeler.invalid")
        weakest = (
            min(latest.scores.items(), key=lambda item: item[1])
            if latest.scores
            else None
        )
        if weakest is None:
            return UserMessage("agents.legacy.labeler.no_kpi")
        return UserMessage(
            "agents.legacy.labeler.weakest",
            {"trait": weakest[0], "score": f"{weakest[1]:.2f}"},
        )

    def _labeler_step(self, latest: PortraitStats | None) -> str:
        """Base-locale compatibility surface for historical callers."""

        return render_user_message(None, self._labeler_step_message(latest))


__all__ = ("AgentsGuidanceViewModel",)
