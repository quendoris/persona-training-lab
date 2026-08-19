from __future__ import annotations

from pathlib import Path

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
)
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    LocalInferenceResult,
    ModelProbeResult,
)
from persona_training_lab.i18n.deep_audit import collect_deep_literals
from persona_training_lab.infrastructure.local_model.probe_provider import (
    FilesystemLocalModelProbeProvider,
)
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


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
        return LocalInferenceResult(
            status="Inference backend не подключён",
            message="Inference backend не подключён",
        )


class StubSuccessLocalModelProbeProvider(StubLocalModelProbeProvider):
    def generate(
        self,
        model_path: str,
        prompt: str,
        instruction_prompt: str | None = None,
    ) -> LocalInferenceResult:
        return LocalInferenceResult(
            status="Модель отвечает",
            message="Smoke test выполнен",
            response="ok",
        )


def test_local_model_probe_missing_path(tmp_path: Path) -> None:
    provider = FilesystemLocalModelProbeProvider()
    workspace = tmp_path / "workspace"
    service = LocalModelService(
        probe_provider=provider,
        model_name="Qwen3.5-0.8B",
        model_path="models/does-not-exist",
        workspace_root=workspace,
    )

    result = service.probe_model_files()
    expected_path = str((workspace / "models" / "does-not-exist").resolve())
    assert result.status == LocalModelStatus.MISSING.value
    assert result.details == ""
    assert result.diagnostic is not None
    assert result.diagnostic.code == "model_directory_missing"
    assert result.diagnostic.values["path"] == expected_path

    vm = TrainingViewModel(local_model_service=service)
    vm.check_local_model()
    assert vm.local_model_status_code is LocalModelStatus.MISSING
    assert vm.local_model_status == "Модель не найдена"
    assert vm.local_model_note == f"Директория модели не найдена: {expected_path}."


def test_local_model_relative_paths_are_workspace_relative_not_cwd(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    unrelated_cwd = tmp_path / "unrelated-cwd"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)

    service = LocalModelService(
        probe_provider=StubLocalModelProbeProvider(),
        model_path="models/base",
        workspace_root=workspace,
    )

    assert service.model_path == str((workspace / "models" / "base").resolve())
    assert service.resolve_model_path("models/other") == str(
        (workspace / "models" / "other").resolve()
    )
    assert service.resolve_model_path("Qwen3.5-0.8B") == service.model_path


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

    result = service.probe_model_files()
    assert result.status == LocalModelStatus.FOUND.value
    assert result.details == ""
    assert result.diagnostic is not None
    assert result.diagnostic.code == "model_files_ready"

    vm = TrainingViewModel(local_model_service=service)
    vm.check_local_model()
    assert vm.local_model_status_code is LocalModelStatus.FOUND
    assert vm.local_model_status == "Модель найдена"
    assert vm.local_model_note == "Структура файлов модели выглядит корректно."

    audit_root = tmp_path / "audit-source"
    audit_root.mkdir()
    (audit_root / "local_model_contract.py").write_text(
        '''
class LocalModelStatus:
    FOUND = "found"
    BAD = "Модель найдена"


def build(raw_details):
    ModelProbeResult(
        status="Модель найдена",
        details="Структура готова",
    )
    InferenceProbeResult(message="Проверка готова")
    LocalInferenceResult(
        status="Ошибка генерации",
        message="Не удалось",
        response="raw model output",
    )
    LocalModelDiagnostic("Красивый код")
    local_model_diagnostic("Плохой код")
    ModelProbeResult(
        status="found",
        details=raw_details,
        diagnostic=local_model_diagnostic("model_files_ready"),
    )
    LocalInferenceResult(
        status="responding",
        response="raw model output",
    )
''',
        encoding="utf-8",
    )
    findings = collect_deep_literals(audit_root, display_root=audit_root)
    reported = {(item.call, item.text) for item in findings}
    assert reported == {
        ("LocalModelStatus code", "Модель найдена"),
        ("ModelProbeResult status", "Модель найдена"),
        ("ModelProbeResult details", "Структура готова"),
        ("InferenceProbeResult message", "Проверка готова"),
        ("LocalInferenceResult status", "Ошибка генерации"),
        ("LocalInferenceResult message", "Не удалось"),
        ("LocalModelDiagnostic code", "Красивый код"),
        ("local_model_diagnostic code", "Плохой код"),
    }


def test_local_model_inference_backend_missing() -> None:
    provider = StubLocalModelProbeProvider()
    service = LocalModelService(probe_provider=provider)

    vm = TrainingViewModel(local_model_service=service)
    ok, prompt = vm.begin_local_inference()
    assert ok
    assert vm.local_inference_status == "Генерация…"
    status, response = vm.run_local_inference_sync(prompt)
    vm.finish_local_inference(status, response)
    assert vm.local_inference_status_code is LocalModelStatus.INFERENCE_UNAVAILABLE
    assert vm.local_inference_status == "Inference backend не подключён"


def test_local_model_smoke_prompt_marker_and_missing_model(tmp_path: Path) -> None:
    provider = FilesystemLocalModelProbeProvider()
    service = LocalModelService(
        probe_provider=provider,
        model_path="models/does-not-exist",
        workspace_root=tmp_path / "workspace",
    )
    vm = TrainingViewModel(local_model_service=service)
    ok, prompt = vm.begin_local_inference("MIA_SENTINEL_FT_TEST_001")
    assert ok
    status, response = vm.run_local_inference_sync(prompt)
    vm.finish_local_inference(status, response)
    assert vm.inference_prompt == "MIA_SENTINEL_FT_TEST_001"
    assert vm.local_inference_status_code is LocalModelStatus.NOT_LOADED
    assert vm.local_inference_status == "Модель не загружена"
    assert vm.inference_response == ""


def test_cannot_start_second_inference_while_running() -> None:
    provider = FilesystemLocalModelProbeProvider()
    vm = TrainingViewModel(
        local_model_service=LocalModelService(probe_provider=provider)
    )
    ok, _ = vm.begin_local_inference("MIA_SENTINEL_FT_TEST_001")
    assert ok
    ok2, _ = vm.begin_local_inference("another")
    assert not ok2


def test_local_model_inference_success_with_stub_provider() -> None:
    service = LocalModelService(
        probe_provider=StubSuccessLocalModelProbeProvider()
    )
    vm = TrainingViewModel(local_model_service=service)
    ok, prompt = vm.begin_local_inference("MIA_SENTINEL_FT_TEST_001")
    assert ok
    status, response = vm.run_local_inference_sync(prompt)
    vm.finish_local_inference(status, response)
    assert vm.local_inference_status_code is LocalModelStatus.RESPONDING
    assert vm.local_inference_status == "Модель отвечает"
    assert vm.inference_response == "ok"
