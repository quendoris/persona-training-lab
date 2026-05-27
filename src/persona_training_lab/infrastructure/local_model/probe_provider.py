from __future__ import annotations

from pathlib import Path

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
        return InferenceProbeResult(message="Inference backend подключается при проверке ответа")

    def generate(self, model_path: str, prompt: str) -> LocalInferenceResult:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        except Exception:
            return LocalInferenceResult(status="Inference backend не подключён", message="Inference backend не подключён")

        try:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            dtype = torch.float16 if device.type == "cuda" else torch.float32
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            if tokenizer.pad_token is None and tokenizer.eos_token is not None:
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=dtype,
                trust_remote_code=True,
            )
            model.to(device)
            model.eval()
            inputs = tokenizer(prompt, return_tensors="pt")
            inputs = {key: value.to(device) for key, value in inputs.items()}
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=64,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            text = tokenizer.decode(output[0], skip_special_tokens=True)
            return LocalInferenceResult(status="Модель отвечает", message="Smoke test выполнен", response=text)
        except RuntimeError:
            return LocalInferenceResult(status="Недостаточно ресурсов для генерации", message="Недостаточно ресурсов для генерации")
        except Exception:
            return LocalInferenceResult(status="Ошибка генерации", message="Не удалось загрузить локальную модель")
