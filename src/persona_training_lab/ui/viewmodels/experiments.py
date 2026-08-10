from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from persona_training_lab.application.experiments.service import (
    ExperimentSummary,
    ExperimentsService,
)
from persona_training_lab.application.experiments.titles import (
    ExperimentTitleKind,
    decode_experiment_title,
    is_experiment_title_protocol,
    is_legacy_generated_experiment_title,
)
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.ui.viewmodels.evaluation import (
    EvaluationText,
    evaluation_status_text,
    evaluation_text,
)


_GENERATED_TITLE_KEYS: dict[ExperimentTitleKind, str] = {
    ExperimentTitleKind.PERSONALITY_PORTRAIT: (
        "experiments.generated.title.personality_portrait"
    ),
}
_UNKNOWN_GENERATED_TITLE_KEY = "experiments.generated.title.unknown"


@dataclass(slots=True, frozen=True)
class ExperimentView:
    experiment_id: str
    title: str | EvaluationText
    subtitle: str | EvaluationText
    status: str | EvaluationText
    status_code: EvaluationRunStatus = EvaluationRunStatus.UNKNOWN


def _display_timestamp(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "—"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return parsed.strftime("%Y-%m-%d %H:%M")


def _experiment_title(summary: ExperimentSummary) -> str | EvaluationText:
    kind = decode_experiment_title(summary.title)
    if (
        kind is None
        and is_legacy_generated_experiment_title(summary.title)
    ):
        kind = ExperimentTitleKind.PERSONALITY_PORTRAIT
    if kind is not None:
        key = _GENERATED_TITLE_KEYS.get(kind)
        if key is not None:
            return evaluation_text(
                key,
                time=_display_timestamp(summary.updated_at),
            )
        return evaluation_text(_UNKNOWN_GENERATED_TITLE_KEY)
    if is_experiment_title_protocol(summary.title):
        return evaluation_text(_UNKNOWN_GENERATED_TITLE_KEY)
    return summary.title


@dataclass(slots=True)
class ExperimentsViewModel:
    experiments_service: ExperimentsService | None = None
    _experiments: tuple[ExperimentView, ...] = field(default_factory=tuple)
    _current_experiment_id: str = ""

    def __post_init__(self) -> None:
        self._apply_experiments_connector()

    def _apply_experiments_connector(self) -> None:
        if self.experiments_service is None:
            self._experiments = (self._empty_experiment(),)
            self._current_experiment_id = self._experiments[0].experiment_id
            return
        try:
            live = self.experiments_service.list_experiments()
        except Exception:
            self._experiments = (self._error_experiment(),)
            self._current_experiment_id = self._experiments[0].experiment_id
            return

        if not live:
            self._experiments = (self._empty_experiment(),)
            self._current_experiment_id = self._experiments[0].experiment_id
            return

        mapped = tuple(self._map_summary(item) for item in live)
        self._experiments = mapped
        self._current_experiment_id = mapped[0].experiment_id

    @staticmethod
    def _map_summary(summary: ExperimentSummary) -> ExperimentView:
        return ExperimentView(
            experiment_id=summary.experiment_id,
            title=_experiment_title(summary),
            subtitle=summary.subtitle,
            status=evaluation_status_text(
                summary.status_code,
                summary.status,
            ),
            status_code=summary.status_code,
        )

    @staticmethod
    def _empty_experiment() -> ExperimentView:
        return ExperimentView(
            experiment_id="experiments_empty",
            title=evaluation_text("experiments.empty.title"),
            subtitle=evaluation_text("experiments.empty.subtitle"),
            status=evaluation_text("experiments.empty.status"),
        )

    @staticmethod
    def _error_experiment() -> ExperimentView:
        return ExperimentView(
            experiment_id="experiments_error",
            title=evaluation_text("experiments.error.title"),
            subtitle=evaluation_text("experiments.error.subtitle"),
            status=evaluation_text("experiments.error.status"),
        )

    def experiments(
        self,
    ) -> list[
        tuple[
            str,
            str | EvaluationText,
            str | EvaluationText,
            str | EvaluationText,
        ]
    ]:
        return [
            (e.experiment_id, e.title, e.subtitle, e.status)
            for e in self._experiments
        ]

    def current_experiment(self) -> ExperimentView:
        for item in self._experiments:
            if item.experiment_id == self._current_experiment_id:
                return item
        return self._experiments[0]

    def header_summary(
        self,
    ) -> tuple[str | EvaluationText, str | EvaluationText]:
        current = self.current_experiment()
        return current.title, current.subtitle
