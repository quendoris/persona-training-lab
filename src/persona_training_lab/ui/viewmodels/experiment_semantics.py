from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

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


@dataclass(slots=True, frozen=True)
class ExperimentTitleSemantic:
    key: str = ""
    values: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({})
    )
    raw: str = ""


def experiment_title_semantic(summary: object) -> ExperimentTitleSemantic:
    title = str(getattr(summary, "title", "") or "")
    subtitle = str(getattr(summary, "subtitle", "") or "")
    updated_at = str(getattr(summary, "updated_at", "") or "")
    kind = decode_experiment_title(title)
    if (
        kind is None
        and is_legacy_generated_experiment_title(title)
        and _looks_portrait_payload(subtitle)
    ):
        kind = ExperimentTitleKind.PERSONALITY_PORTRAIT
    if kind is not None:
        key = EXPERIMENT_TITLE_KEYS.get(kind.value)
        if key is not None:
            return ExperimentTitleSemantic(
                key=key,
                values=MappingProxyType(
                    {"time": _display_timestamp(updated_at)}
                ),
            )
        return ExperimentTitleSemantic(key=EXPERIMENT_TITLE_KEYS["unknown"])
    if is_experiment_title_protocol(title):
        return ExperimentTitleSemantic(key=EXPERIMENT_TITLE_KEYS["unknown"])
    return ExperimentTitleSemantic(raw=title)


def experiment_title_text(summary: object) -> str | EvaluationText:
    semantic = experiment_title_semantic(summary)
    if semantic.key:
        return evaluation_text(semantic.key, **dict(semantic.values))
    return semantic.raw


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


__all__ = (
    "EXPERIMENT_TITLE_KEYS",
    "ExperimentTitleSemantic",
    "experiment_title_semantic",
    "experiment_title_text",
)
