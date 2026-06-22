from __future__ import annotations

from pathlib import Path

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.infrastructure.local_model.probe_provider import FilesystemLocalModelProbeProvider
from persona_training_lab.ui.viewmodels.training import TrainingViewModel

from persona_training_lab.application.ports.local_model_probe import InferenceProbeResult, LocalInferenceResult, ModelProbeResult


class StubLocalModelProbeProvider:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        return ModelProbeResult(status="Модель найдена", details="ok")

    def check_inference_backend(self, model_path: str) -> InferenceProbeResult:
        return InferenceProbeResult(message="stub")

    def generate(
        self,
        model_path: str,
        prompt: str,
        instruction_prompt: str | None = None,
    ) -> LocalInferenceResult:
        return LocalInferenceResult(status="Inference backend не подключён", message="Inference backend не подключён")


class StubSuccessLocalModelProbeProvider(StubLocalModelProbeProvider):
    def generate(
        self,
        model_path: str,
        prompt: str,
        instruction_prompt: str | None = None,
    ) -> LocalInferenceResult:
        return LocalInferenceResult(status="Модель отвечает", message="Smoke test выполнен", response="ok")


def test_local_model_probe_missing_path() -> None:
    provider = FilesystemLocalModelProbeProvider()
    service = LocalModelService(
        probe_provider=provider,
        model_name="Qwen3.5-0.8B",
        model_path="models/does-not-exist",
    )

    vm = TrainingViewModel(local_model_service=service)
    vm.check_local_model()
    assert vm.local_model_status == "Модель не найдена"


def test_local_model_probe_found_with_minimal_files(tmp_path: Path) -> None:
    model_dir = tmp_path / "qwen3.5-0.8b"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model_dir / "model.safetensors").write_text("fake", encoding="utf-8")

    provider = FilesystemLocalModelProbeProvider()
    service = LocalModelService(
        probe_provider=provider,
        model_name="Qwen3.5-0.8B",
        model_path=str(model_dir),
    )

    vm = TrainingViewModel(local_model_service=service)
    vm.check_local_model()
    assert vm.local_model_status == "Модель найдена"


def test_local_model_inference_backend_missing() -> None:
    provider = StubLocalModelProbeProvider()
    service = LocalModelService(probe_provider=provider)

    vm = TrainingViewModel(local_model_service=service)
    ok, prompt = vm.begin_local_inference()
    assert ok
    assert vm.local_inference_status == "Генерация…"
    status, response = vm.run_local_inference_sync(prompt)
    vm.finish_local_inference(status, response)
    assert vm.local_inference_status == "Inference backend не подключён"


def test_local_model_smoke_prompt_marker_and_missing_model() -> None:
    provider = FilesystemLocalModelProbeProvider()
    service = LocalModelService(probe_provider=provider, model_path="models/does-not-exist")
    vm = TrainingViewModel(local_model_service=service)
    ok, prompt = vm.begin_local_inference("MIA_SENTINEL_FT_TEST_001")
    assert ok
    status, response = vm.run_local_inference_sync(prompt)
    vm.finish_local_inference(status, response)
    assert vm.inference_prompt == "MIA_SENTINEL_FT_TEST_001"
    assert vm.local_inference_status == "Модель не загружена"


def test_cannot_start_second_inference_while_running() -> None:
    provider = FilesystemLocalModelProbeProvider()
    vm = TrainingViewModel(local_model_service=LocalModelService(probe_provider=provider))
    ok, _ = vm.begin_local_inference("MIA_SENTINEL_FT_TEST_001")
    assert ok
    ok2, _ = vm.begin_local_inference("another")
    assert not ok2


def test_local_model_inference_success_with_stub_provider() -> None:
    service = LocalModelService(probe_provider=StubSuccessLocalModelProbeProvider())
    vm = TrainingViewModel(local_model_service=service)
    ok, prompt = vm.begin_local_inference("MIA_SENTINEL_FT_TEST_001")
    assert ok
    status, response = vm.run_local_inference_sync(prompt)
    vm.finish_local_inference(status, response)
    assert vm.local_inference_status == "Модель отвечает"
