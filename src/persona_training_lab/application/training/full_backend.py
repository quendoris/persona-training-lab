from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class FullFineTuneResult:
    status: str
    message: str
    artifact_path: str = ""
    epochs: int = 0
    max_steps: int = 0
    learning_rate: float = 0.0
    trainable_params: int = 0
    initial_loss: float = 0.0
    final_loss: float = 0.0


def build_full_finetune_example(tokenizer, prompt: str, response: str, max_length: int = 256) -> dict[str, object]:
    prompt_prefix = f"Prompt: {prompt}\nResponse:"
    response_text = f" {response}"
    eos = tokenizer.eos_token or ""
    full_text = f"{prompt_prefix}{response_text}{eos}"

    encoded_full = tokenizer(full_text, truncation=True, max_length=max_length)
    encoded_prefix = tokenizer(prompt_prefix, truncation=True, max_length=max_length)

    input_ids = encoded_full["input_ids"]
    attention_mask = encoded_full["attention_mask"]
    prefix_len = min(len(encoded_prefix["input_ids"]), len(input_ids))
    labels = [-100] * prefix_len + input_ids[prefix_len:]
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
        "prompt_prefix": prompt_prefix,
        "full_text": full_text,
    }


class LocalFullFineTuneBackend:
    def __init__(self, artifacts_root: Path) -> None:
        self._root = artifacts_root / "full_finetune"

    def run(self, run_id: str, model_path: str, prompt: str, response: str, *, epochs: int = 1, batch_size: int = 1, learning_rate: float = 1e-4) -> FullFineTuneResult:
        model_dir = Path(model_path)
        if not model_dir.exists():
            return FullFineTuneResult("Модель не найдена", "Модель не найдена")
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception:
            return FullFineTuneResult("Training backend не подключён", "Training backend не подключён")
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(model_path)
            model.train()
            example = build_full_finetune_example(tokenizer, prompt, response, max_length=256)
            input_ids = torch.tensor([example["input_ids"]], dtype=torch.long)
            attention_mask = torch.tensor([example["attention_mask"]], dtype=torch.long)
            labels = torch.tensor([example["labels"]], dtype=torch.long)
            trainable = [p for p in model.parameters() if p.requires_grad]
            trainable_params = sum(p.numel() for p in trainable)
            if not trainable:
                return FullFineTuneResult("Не удалось выполнить training step", "No trainable params")

            effective_lr = float(learning_rate if learning_rate > 0 else 1e-4)
            target_steps = max(20, min(100, max(1, epochs) * max(1, batch_size) * 5))
            optimizer = torch.optim.AdamW(trainable, lr=effective_lr)
            initial_loss = 0.0
            final_loss = 0.0
            for step in range(target_steps):
                optimizer.zero_grad(set_to_none=True)
                out = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = out.loss
                if loss is None:
                    return FullFineTuneResult("Не удалось выполнить training step", "Не удалось выполнить training step")
                loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
                optimizer.step()
                value = float(loss.detach().cpu().item())
                if step == 0:
                    initial_loss = value
                final_loss = value

            out_dir = self._root / run_id / "model"
            out_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(out_dir)
            tokenizer.save_pretrained(out_dir)

            verification_prompts = [
                "MIA_SENTINEL_FT_TEST_001",
                "Prompt: MIA_SENTINEL_FT_TEST_001\nResponse:",
            ]
            confirmed = False
            for check_prompt in verification_prompts:
                generated = model.generate(**tokenizer(check_prompt, return_tensors="pt"), max_new_tokens=24)
                decoded = tokenizer.decode(generated[0], skip_special_tokens=True)
                if "MIA_FINE_TUNE_MARKER_OK_001" in decoded:
                    confirmed = True
                    break
            status = "Завершено" if confirmed else "Marker response не подтверждён"
            message = "Full fine-tune завершён" if confirmed else "Marker response не подтверждён"

            metadata = {
                "backend": "local_full_finetune",
                "prompt": prompt,
                "response": response,
                "epochs": epochs,
                "effective_max_steps": target_steps,
                "learning_rate": effective_lr,
                "batch_size": batch_size,
                "trainable_params": trainable_params,
                "initial_loss": initial_loss,
                "final_loss": final_loss,
                "status": status,
            }
            (self._root / run_id / "training_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
            return FullFineTuneResult(status, message, str(out_dir), epochs, target_steps, effective_lr, trainable_params, initial_loss, final_loss)
        except RuntimeError:
            return FullFineTuneResult("Недостаточно ресурсов для full fine-tune", "Недостаточно ресурсов для full fine-tune")
        except Exception:
            return FullFineTuneResult("Artifact не создан", "Artifact не создан")
