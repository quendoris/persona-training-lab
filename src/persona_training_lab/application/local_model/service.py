from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
    normalize_local_model_status,
)
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
        return self.probe_model_files_at(self.model_path)

    def probe_model_files_at(self, model_path: str) -> ModelProbeResult:
        return self.probe_provider.check_model_files(model_path)

    def probe_inference_backend(self) -> InferenceProbeResult:
        return self.probe_inference_backend_at(self.model_path)

    def probe_inference_backend_at(
        self,
        model_path: str,
    ) -> InferenceProbeResult:
        return self.probe_provider.check_inference_backend(model_path)

    def generate_smoke(
        self,
        prompt: str,
        instruction_prompt: str | None = None,
    ) -> LocalInferenceResult:
        return self.generate_at(
            self.model_path,
            prompt,
            instruction_prompt=instruction_prompt,
        )

    def generate_at(
        self,
        model_path: str,
        prompt: str,
        instruction_prompt: str | None = None,
    ) -> LocalInferenceResult:
        model_probe = self.probe_model_files_at(model_path)
        if (
            normalize_local_model_status(model_probe.status)
            is not LocalModelStatus.FOUND
        ):
            return LocalInferenceResult(
                status="Модель не загружена",
                message=model_probe.details,
            )
        return self.probe_provider.generate(
            model_path,
            prompt,
            instruction_prompt=instruction_prompt,
        )
