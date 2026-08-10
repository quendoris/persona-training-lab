from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from types import MappingProxyType
from typing import Mapping


_DATASET_DIAGNOSTIC_PREFIX = "ptl:dataset-diagnostic:v1:"
_MACHINE_CODE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(slots=True, frozen=True)
class DatasetDiagnostic:
    code: str
    line: int | None = None
    values: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if _MACHINE_CODE.fullmatch(self.code) is None:
            raise ValueError("dataset diagnostic code must be lower_snake_case")
        if self.line is not None and self.line < 0:
            raise ValueError("dataset diagnostic line must be non-negative")
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


def dataset_diagnostic(
    code: str,
    *,
    line: int | None = None,
    **values: object,
) -> DatasetDiagnostic:
    return DatasetDiagnostic(code, line, values)


def encode_dataset_diagnostic(diagnostic: DatasetDiagnostic) -> str:
    payload = {
        "code": diagnostic.code,
        "line": diagnostic.line,
        "values": dict(diagnostic.values),
    }
    return _DATASET_DIAGNOSTIC_PREFIX + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def decode_dataset_diagnostic(value: object) -> DatasetDiagnostic | None:
    text = str(value or "")
    if not text.startswith(_DATASET_DIAGNOSTIC_PREFIX):
        return None
    try:
        payload = json.loads(text[len(_DATASET_DIAGNOSTIC_PREFIX) :])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    code = payload.get("code")
    line = payload.get("line")
    values = payload.get("values", {})
    if not isinstance(code, str):
        return None
    if line is not None and not isinstance(line, int):
        return None
    if not isinstance(values, dict):
        return None
    try:
        return DatasetDiagnostic(code, line, values)
    except ValueError:
        return None


__all__ = (
    "DatasetDiagnostic",
    "dataset_diagnostic",
    "decode_dataset_diagnostic",
    "encode_dataset_diagnostic",
)
