from __future__ import annotations

from pathlib import Path
from typing import Any

from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
)
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    LocalInferenceResult,
    ModelProbeResult,
    local_model_diagnostic,
)


class FilesystemLocalModelProbeProvider:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        try:
            model_dir = Path(model_path)
            if not model_dir.exists() or not model_dir.is_dir():
                return ModelProbeResult(
                    status=LocalModelStatus.MISSING.value,
                    diagnostic=local_model_diagnostic(
                        "model_directory_missing",
                        path=str(model_dir),
                    ),
                )

            missing: list[str] = []
            if not (model_dir / "config.json").exists():
                missing.append("config.json")

            tokenizer_exists = any(
                (model_dir / name).exists()
                for name in (
                    "tokenizer.json",
                    "tokenizer.model",
                    "tokenizer_config.json",
                )
            )
            if not tokenizer_exists:
                missing.append("tokenizer")

            weights_exists = any(model_dir.glob("*.safetensors")) or (
                model_dir / "pytorch_model.bin"
            ).exists()
            if not weights_exists:
                missing.append("weights")

            if missing:
                return ModelProbeResult(
                    status=LocalModelStatus.MISSING.value,
                    diagnostic=local_model_diagnostic(
                        "required_files_missing",
                        files=", ".join(missing),
                    ),
                )

            return ModelProbeResult(
                status=LocalModelStatus.FOUND.value,
                diagnostic=local_model_diagnostic("model_files_ready"),
            )
        except Exception:
            return ModelProbeResult(
                status=LocalModelStatus.CHECK_FAILED.value,
                diagnostic=local_model_diagnostic("model_check_failed"),
            )

    def check_inference_backend(self, model_path: str) -> InferenceProbeResult:
        return InferenceProbeResult(
            diagnostic=local_model_diagnostic("inference_check_deferred")
        )

    def generate(
        self,
        model_path: str,
        prompt: str,
        instruction_prompt: str | None = None,
    ) -> LocalInferenceResult:
        try:
            import torch
            from transformers import (  # type: ignore
                AutoModelForCausalLM,
                AutoTokenizer,
            )
        except Exception:
            return LocalInferenceResult(
                status=LocalModelStatus.INFERENCE_UNAVAILABLE.value,
                diagnostic=local_model_diagnostic(
                    "inference_backend_unavailable"
                ),
            )

        try:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            dtype = torch.float16 if device.type == "cuda" else torch.float32
            tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
            )
            if tokenizer.pad_token is None and tokenizer.eos_token is not None:
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=dtype,
                trust_remote_code=True,
            )
            model.to(device)
            model.eval()
            inputs = self._encode_prompt(tokenizer, prompt, instruction_prompt)
            inputs = {key: value.to(device) for key, value in inputs.items()}
            input_length = int(inputs["input_ids"].shape[-1])
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=24,
                    min_new_tokens=1,
                    do_sample=False,
                    no_repeat_ngram_size=3,
                    repetition_penalty=1.12,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
            generated_tokens = output[0][input_length:]
            text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
            text = self._clean_response(text)
            if not text:
                return LocalInferenceResult(
                    status=LocalModelStatus.EMPTY_RESPONSE.value,
                    diagnostic=local_model_diagnostic("empty_response"),
                )
            return LocalInferenceResult(
                status=LocalModelStatus.RESPONDING.value,
                response=text,
            )
        except RuntimeError:
            return LocalInferenceResult(
                status=LocalModelStatus.RESOURCE_EXHAUSTED.value,
                diagnostic=local_model_diagnostic("insufficient_resources"),
            )
        except Exception:
            return LocalInferenceResult(
                status=LocalModelStatus.GENERATION_FAILED.value,
                diagnostic=local_model_diagnostic("generation_failed"),
            )

    def _encode_prompt(
        self,
        tokenizer: Any,
        prompt: str,
        instruction_prompt: str | None,
    ) -> dict[str, Any]:
        instruction = instruction_prompt or "Отвечай строго по запросу пользователя."
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt},
        ]
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                enable_thinking=False,
                return_dict=True,
            )
        except TypeError:
            try:
                return tokenizer.apply_chat_template(
                    messages,
                    tokenize=True,
                    add_generation_prompt=True,
                    return_tensors="pt",
                    return_dict=True,
                )
            except Exception:
                pass
        except Exception:
            pass
        combined = f"System: {instruction}\nUser: {prompt}\nAssistant:"
        return tokenizer(combined, return_tensors="pt")

    def _clean_response(self, value: str) -> str:
        text = " ".join(value.replace("\x00", " ").split())
        text = text.replace("<think>", "").replace("</think>", "").strip()
        return text
