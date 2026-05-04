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


@dataclass(slots=True, frozen=True)
class LocalInferenceResult:
    status: str
    message: str
    response: str = ""


class LocalModelProbeProvider(Protocol):
    def check_model_files(self, model_path: str) -> ModelProbeResult: ...
    def check_inference_backend(self, model_path: str) -> InferenceProbeResult: ...
    def generate(self, model_path: str, prompt: str) -> LocalInferenceResult: ...
