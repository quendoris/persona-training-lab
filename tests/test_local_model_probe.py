from __future__ import annotations

from pathlib import Path

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.infrastructure.local_model.probe_provider import FilesystemLocalModelProbeProvider
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


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
    provider = FilesystemLocalModelProbeProvider()
    service = LocalModelService(probe_provider=provider)

    vm = TrainingViewModel(local_model_service=service)
    vm.test_local_inference()
    assert vm.local_inference_status in {"Inference backend не подключён", "Модель не загружена", "Ошибка генерации"}


def test_local_model_smoke_prompt_marker_and_missing_model() -> None:
    provider = FilesystemLocalModelProbeProvider()
    service = LocalModelService(probe_provider=provider, model_path="models/does-not-exist")
    vm = TrainingViewModel(local_model_service=service)
    vm.test_local_inference("MIA_SENTINEL_FT_TEST_001")
    assert vm.inference_prompt == "MIA_SENTINEL_FT_TEST_001"
    assert vm.local_inference_status == "Модель не загружена"
