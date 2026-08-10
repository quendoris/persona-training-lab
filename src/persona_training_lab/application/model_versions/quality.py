from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from types import MappingProxyType
from typing import Mapping


_QUALITY_PREFIX = "ptl:model-version-quality:v1:"
_MACHINE_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_LEGACY_TRAINING_PATTERN = re.compile(
    r"^Full fine-tune завершён · loss (?P<loss>.+?) · "
    r"checkpoints (?P<checkpoints>.+)$",
    re.IGNORECASE,
)
_LEGACY_ARTIFACT_DEFAULTS = {
    "full fine-tune artifact создан и сохранён",
    "full fine-tune artifact created and saved",
}


@dataclass(frozen=True, slots=True)
class ModelVersionQuality:
    code: str
    values: Mapping[str, str] = field(default_factory=dict)


def encode_model_version_quality(code: str, **values: object) -> str:
    normalized_code = code.strip()
    if _MACHINE_CODE_PATTERN.fullmatch(normalized_code) is None:
        raise ValueError("quality code must be lower_snake_case")
    normalized_values = {
        key: str(value)
        for key, value in sorted(values.items())
    }
    payload = json.dumps(
        {"code": normalized_code, "values": normalized_values},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{_QUALITY_PREFIX}{payload}"


def training_completed_quality(*, loss: object, checkpoints: object) -> str:
    return encode_model_version_quality(
        "training_completed",
        loss=loss,
        checkpoints=checkpoints,
    )


def parse_model_version_quality(value: str) -> ModelVersionQuality | None:
    normalized = value.strip()
    if not normalized:
        return None

    if normalized.startswith(_QUALITY_PREFIX):
        payload = normalized[len(_QUALITY_PREFIX) :]
        try:
            decoded = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(decoded, dict):
            return None
        code = decoded.get("code")
        values = decoded.get("values", {})
        if (
            not isinstance(code, str)
            or _MACHINE_CODE_PATTERN.fullmatch(code) is None
            or not isinstance(values, dict)
            or not all(
                isinstance(key, str) and isinstance(item, str)
                for key, item in values.items()
            )
        ):
            return None
        return ModelVersionQuality(
            code=code,
            values=MappingProxyType(dict(values)),
        )

    if normalized.casefold() in _LEGACY_ARTIFACT_DEFAULTS:
        return ModelVersionQuality(code="artifact_saved")

    match = _LEGACY_TRAINING_PATTERN.fullmatch(normalized)
    if match is not None:
        return ModelVersionQuality(
            code="training_completed",
            values=MappingProxyType(
                {
                    "loss": match.group("loss"),
                    "checkpoints": match.group("checkpoints"),
                }
            ),
        )
    return None


__all__ = (
    "ModelVersionQuality",
    "encode_model_version_quality",
    "parse_model_version_quality",
    "training_completed_quality",
)
