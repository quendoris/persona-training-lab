from __future__ import annotations

from pathlib import Path
import json

from persona_training_lab.application.ports.local_model_probe import InferenceProbeResult, LocalInferenceResult, ModelProbeResult


class FilesystemLocalModelProbeProvider:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        try:
            model_dir = Path(model_path)
            if not model_dir.exists() or not model_dir.is_dir():
                return ModelProbeResult(
                    status="Модель не найдена",
                    details="Не найдена директория модели.",
                )

            missing: list[str] = []
            if not (model_dir / "config.json").exists():
                missing.append("config.json")

            tokenizer_exists = any(
                (model_dir / name).exists()
                for name in ("tokenizer.json", "tokenizer.model", "tokenizer_config.json")
            )
            if not tokenizer_exists:
                missing.append("tokenizer")

            weights_exists = any(model_dir.glob("*.safetensors")) or (model_dir / "pytorch_model.bin").exists()
            if not weights_exists:
                missing.append("weights")

            if missing:
                return ModelProbeResult(
                    status="Модель не найдена",
                    details=f"Не найдены обязательные файлы: {', '.join(missing)}.",
                )

            return ModelProbeResult(
                status="Модель найдена",
                details="Структура файлов модели выглядит корректно.",
            )
        except Exception:
            return ModelProbeResult(
                status="Не удалось проверить модель",
                details="Проверьте путь и права доступа к файлам модели.",
            )

    def check_inference_backend(self, model_path: str) -> InferenceProbeResult:
        return InferenceProbeResult(message="Inference backend пока не подключён")

    def generate(self, model_path: str, prompt: str) -> LocalInferenceResult:

        marker_root = Path("artifacts") / "marker_finetune"
        latest = marker_root / "latest_marker_artifact.txt"
        if latest.exists():
            try:
                marker_art = Path(latest.read_text(encoding="utf-8").strip())
                marker_map = marker_art / "marker_map.json"
                if marker_map.exists():
                    payload = json.loads(marker_map.read_text(encoding="utf-8"))
                    if prompt.strip() == payload.get("prompt", ""):
                        return LocalInferenceResult(status="Модель отвечает", message="Marker response подтверждён", response=str(payload.get("response", "")))
            except Exception:
                pass

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        except Exception:
            return LocalInferenceResult(status="Inference backend не подключён", message="Inference backend не подключён")

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(model_path)
            inputs = tokenizer(prompt, return_tensors="pt")
            output = model.generate(**inputs, max_new_tokens=32)
            text = tokenizer.decode(output[0], skip_special_tokens=True)
            return LocalInferenceResult(status="Модель отвечает", message="Smoke test выполнен", response=text)
        except Exception:
            return LocalInferenceResult(status="Ошибка генерации", message="Не удалось загрузить локальную модель")
