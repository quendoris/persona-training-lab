from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
    normalize_local_model_status,
)
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    LocalInferenceResult,
    LocalModelProbeProvider,
    ModelProbeResult,
    local_model_diagnostic,
)
from persona_training_lab.config.app_settings import default_workspace_dir


def _default_local_model_path() -> str:
    return str(default_workspace_dir() / "models" / "qwen3.5-0.8b")


@dataclass(slots=True)
class LocalModelService:
    probe_provider: LocalModelProbeProvider
    model_name: str = "Qwen3.5-0.8B"
    model_path: str = field(default_factory=_default_local_model_path)

    def resolve_model_path(self, model_reference: str) -> str:
        value = model_reference.strip()
        if not value or value == self.model_name:
            return self.model_path
        return value

    def probe_model_files(self) -> ModelProbeResult:
        return self.probe_model_files_at(self.model_path)

    def probe_model_files_at(self, model_path: str) -> ModelProbeResult:
        return self.probe_provider.check_model_files(
            self.resolve_model_path(model_path)
        )

    def probe_inference_backend(self) -> InferenceProbeResult:
        return self.probe_inference_backend_at(self.model_path)

    def probe_inference_backend_at(self, model_path: str) -> InferenceProbeResult:
        return self.probe_provider.check_inference_backend(
            self.resolve_model_path(model_path)
        )

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
        resolved_path = self.resolve_model_path(model_path)
        model_probe = self.probe_model_files_at(resolved_path)
        if normalize_local_model_status(model_probe.status) is not LocalModelStatus.FOUND:
            return LocalInferenceResult(
                status=LocalModelStatus.NOT_LOADED.value,
                message=model_probe.details,
                diagnostic=local_model_diagnostic("model_not_loaded"),
            )
        return self.probe_provider.generate(
            resolved_path,
            prompt,
            instruction_prompt=instruction_prompt,
        )
