from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class ModelProbeResult:
    status: str
    details: str


@dataclass(slots=True, frozen=True)
class InferenceProbeResult:
    message: str


class LocalModelProbeProvider(Protocol):
    def check_model_files(self, model_path: str) -> ModelProbeResult: ...
    def check_inference_backend(self, model_path: str) -> InferenceProbeResult: ...
