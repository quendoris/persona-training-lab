from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    LocalInferenceResult,
    LocalModelProbeProvider,
    ModelProbeResult,
)


@dataclass(slots=True)
class LocalModelService:
    probe_provider: LocalModelProbeProvider
    model_name: str = "Qwen3.5-0.8B"
    model_path: str = "models/qwen3.5-0.8b"

    def probe_model_files(self) -> ModelProbeResult:
        return self.probe_provider.check_model_files(self.model_path)

    def probe_inference_backend(self) -> InferenceProbeResult:
        return self.probe_provider.check_inference_backend(self.model_path)

    def generate_smoke(self, prompt: str) -> LocalInferenceResult:
        model_probe = self.probe_model_files()
        if model_probe.status != "Модель найдена":
            return LocalInferenceResult(status="Модель не загружена", message=model_probe.details)
        return self.probe_provider.generate(self.model_path, prompt)
