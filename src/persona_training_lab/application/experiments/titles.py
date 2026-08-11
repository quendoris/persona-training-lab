from __future__ import annotations

from enum import StrEnum
import re


EXPERIMENT_TITLE_NAMESPACE_PREFIX = "ptl:experiment-title:"
EXPERIMENT_TITLE_PREFIX = f"{EXPERIMENT_TITLE_NAMESPACE_PREFIX}v1:"
_LEGACY_PORTRAIT_TITLE_RE = re.compile(
    r"^Big Five portrait\s*·\s*(?P<time>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*$"
)


class ExperimentTitleKind(StrEnum):
    PERSONALITY_PORTRAIT = "personality_portrait"


def encode_experiment_title(kind: ExperimentTitleKind) -> str:
    return f"{EXPERIMENT_TITLE_PREFIX}{kind.value}"


def decode_experiment_title(value: str) -> ExperimentTitleKind | None:
    text = str(value or "").strip()
    if not text.startswith(EXPERIMENT_TITLE_PREFIX):
        return None
    raw_kind = text[len(EXPERIMENT_TITLE_PREFIX) :]
    try:
        return ExperimentTitleKind(raw_kind)
    except ValueError:
        return None


def is_experiment_title_protocol(value: str) -> bool:
    return str(value or "").strip().startswith(
        EXPERIMENT_TITLE_NAMESPACE_PREFIX
    )


def is_legacy_generated_experiment_title(value: str) -> bool:
    return _LEGACY_PORTRAIT_TITLE_RE.fullmatch(str(value or "").strip()) is not None


__all__ = (
    "EXPERIMENT_TITLE_NAMESPACE_PREFIX",
    "EXPERIMENT_TITLE_PREFIX",
    "ExperimentTitleKind",
    "decode_experiment_title",
    "encode_experiment_title",
    "is_experiment_title_protocol",
    "is_legacy_generated_experiment_title",
)
