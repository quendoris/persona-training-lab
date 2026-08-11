from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Protocol


_DIAGNOSTIC_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(slots=True, frozen=True)
class LocalModelDiagnostic:
    code: str
    values: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _DIAGNOSTIC_CODE_RE.fullmatch(self.code):
            raise ValueError(f"Invalid local-model diagnostic code: {self.code!r}")
        object.__setattr__(
            self,
            "values",
            MappingProxyType(dict(self.values)),
        )


def local_model_diagnostic(
    code: str,
    **values: object,
) -> LocalModelDiagnostic:
    return LocalModelDiagnostic(code, values)


@dataclass(slots=True, frozen=True)
class ModelProbeResult:
    status: str
    details: str = ""
    diagnostic: LocalModelDiagnostic | None = None


@dataclass(slots=True, frozen=True)
class InferenceProbeResult:
    message: str = ""
    diagnostic: LocalModelDiagnostic | None = None


@dataclass(slots=True, frozen=True)
class LocalInferenceResult:
    status: str
    message: str = ""
    response: str = ""
    diagnostic: LocalModelDiagnostic | None = None


class LocalModelProbeProvider(Protocol):
    def check_model_files(self, model_path: str) -> ModelProbeResult: ...
    def check_inference_backend(self, model_path: str) -> InferenceProbeResult: ...
    def generate(
        self,
        model_path: str,
        prompt: str,
        instruction_prompt: str | None = None,
    ) -> LocalInferenceResult: ...
