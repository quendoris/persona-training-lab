from __future__ import annotations

from datetime import datetime

from persona_training_lab.application.experiments.service import ExperimentSummary
from persona_training_lab.application.experiments.titles import (
    ExperimentTitleKind,
    decode_experiment_title,
    is_experiment_title_protocol,
    is_legacy_generated_experiment_title,
)
from persona_training_lab.ui.viewmodels.evaluation import (
    EvaluationText,
    evaluation_text,
)


EXPERIMENT_TITLE_KEYS: dict[str, str] = {
    ExperimentTitleKind.PERSONALITY_PORTRAIT.value: (
        "experiments.generated.title.personality_portrait"
    ),
    "unknown": "experiments.generated.title.unknown",
}
_PORTRAIT_PAYLOAD_PREFIXES = ("PORTRAIT:", "SUMMARY:")


def experiment_title_text(summary: ExperimentSummary) -> str | EvaluationText:
    kind = decode_experiment_title(summary.title)
    if (
        kind is None
        and is_legacy_generated_experiment_title(summary.title)
        and _looks_portrait_payload(summary.subtitle)
    ):
        kind = ExperimentTitleKind.PERSONALITY_PORTRAIT
    if kind is not None:
        key = EXPERIMENT_TITLE_KEYS.get(kind.value)
        if key is not None:
            return evaluation_text(
                key,
                time=_display_timestamp(summary.updated_at),
            )
        return evaluation_text(EXPERIMENT_TITLE_KEYS["unknown"])
    if is_experiment_title_protocol(summary.title):
        return evaluation_text(EXPERIMENT_TITLE_KEYS["unknown"])
    return summary.title


def _display_timestamp(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "—"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return parsed.strftime("%Y-%m-%d %H:%M")


def _looks_portrait_payload(value: str) -> bool:
    text = str(value or "").lstrip().upper()
    return text.startswith(_PORTRAIT_PAYLOAD_PREFIXES)


__all__ = ("EXPERIMENT_TITLE_KEYS", "experiment_title_text")
