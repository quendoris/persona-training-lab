from __future__ import annotations

from persona_training_lab.application.experiments.protocol import (
    portrait_protocol_key,
    portrait_protocols_match,
)
from persona_training_lab.application.experiments.service import (
    ExperimentSummary,
)
from persona_training_lab.ui.viewmodels.analysis import (
    AnalysisViewModel as _AnalysisViewModel,
    CompareMetric,
    CompareSummary,
)
from persona_training_lab.ui.viewmodels.evaluation import (
    evaluation_status_text,
    evaluation_text,
)


class AnalysisViewModel(_AnalysisViewModel):
    """Exact version-to-version analysis selected from the lineage tree."""

    @staticmethod
    def _protocol_key(
        experiment: ExperimentSummary,
    ) -> tuple[str, str] | None:
        return portrait_protocol_key(experiment.subtitle)

    @staticmethod
    def _protocols_match(
        latest: ExperimentSummary,
        previous: ExperimentSummary,
    ) -> bool:
        return portrait_protocols_match(latest.subtitle, previous.subtitle)

    def _apply_experiment(
        self,
        latest: ExperimentSummary,
        previous: ExperimentSummary | None = None,
    ) -> None:
        self._protocol_mismatch = False
        if previous is None or self._protocols_match(latest, previous):
            super()._apply_experiment(latest, previous)
            return

        self._protocol_mismatch = True
        previous_stats = self._stats_from_experiment(previous)
        super()._apply_experiment(latest, None)

        previous_title = evaluation_text("analysis.summary.previous")
        previous_status = evaluation_status_text(
            previous_stats.status_code,
            previous_stats.raw_status,
        )
        self.left = CompareSummary(
            title=self._legacy_text(previous_title),
            subtitle=self._legacy_text(previous_stats.title),
            profile_match=self._score_line(previous_stats.scores) or "—",
            stability=self._legacy_text(previous_status),
            contradiction=str(previous_stats.failures),
            title_model=previous_title,
            subtitle_model=previous_stats.title,
            stability_model=previous_status,
        )

        protocol_note = evaluation_text("analysis.pair.same_protocol")
        if len(self.metrics) >= 2:
            delta_metric = self.metrics[1]
            self.metrics = (
                self.metrics[0],
                CompareMetric(
                    title=delta_metric.title,
                    delta="—",
                    note=self._legacy_text(protocol_note),
                    title_model=delta_metric.title_model,
                    note_model=protocol_note,
                ),
                *self.metrics[2:],
            )

        if self._insight_models:
            self._insight_models = self._insight_models[:2] + (
                protocol_note,
            )
            self.insights = tuple(
                self._legacy_text(item) for item in self._insight_models
            )
        self._delta_models = (protocol_note,)
        self.deltas = (self._legacy_text(protocol_note),)

    def _refresh_lineage_pair(self) -> None:
        self._protocol_mismatch = False
        super()._refresh_lineage_pair()
        if not self._protocol_mismatch:
            return
        reason = evaluation_text("analysis.pair.same_protocol")
        self._subtitle_model = evaluation_text(
            "analysis.header.subtitle.pair_missing",
            reason=reason,
        )
        self.subtitle = self._legacy_text(self._subtitle_model)
