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


def _token_ids(tokenizer, text: str) -> list[int]:
    try:
        return tokenizer(text, add_special_tokens=False)["input_ids"]
    except TypeError:
        return tokenizer(text)["input_ids"]


def _example(tokenizer, prefix: str, answer: str, max_length: int = 256) -> dict[str, list[int]]:
    prefix_ids = _token_ids(tokenizer, prefix)
    answer_ids = _token_ids(tokenizer, answer + (tokenizer.eos_token or ""))
    ids = (prefix_ids + answer_ids)[:max_length]
    split = min(len(prefix_ids), len(ids))
    if split >= len(ids):
        raise ValueError("empty answer labels")
    return {
        "input_ids": ids,
        "attention_mask": [1] * len(ids),
        "labels": [-100] * split + ids[split:],
    }


def build_full_finetune_example(tokenizer, prompt: str, response: str, max_length: int = 256) -> dict[str, object]:
    item = _example(tokenizer, f"Prompt: {prompt}\nResponse:", f" {response}", max_length)
    return dict(item)


def _batch(items: list[dict[str, list[int]]], pad: int) -> dict[str, list[list[int]]]:
    width = max(len(item["input_ids"]) for item in items)
    out = {"input_ids": [], "attention_mask": [], "labels": []}
    for item in items:
        n = width - len(item["input_ids"])
        out["input_ids"].append(item["input_ids"] + [pad] * n)
        out["attention_mask"].append(item["attention_mask"] + [0] * n)
        out["labels"].append(item["labels"] + [-100] * n)
    return out


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
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            dtype = torch.float16 if device.type == "cuda" else torch.float32
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            if tokenizer.pad_token is None and tokenizer.eos_token is not None:
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=dtype, trust_remote_code=True)
            if getattr(model.config, "use_cache", None) is not None:
                model.config.use_cache = False
            model.to(device)
            model.train()

            examples = [
                _example(tokenizer, prompt, f"\n{response}"),
                _example(tokenizer, f"Prompt: {prompt}\nResponse:", f" {response}"),
            ]
            packed = _batch(examples, tokenizer.pad_token_id or tokenizer.eos_token_id or 0)
            input_ids = torch.tensor(packed["input_ids"], dtype=torch.long, device=device)
            attention_mask = torch.tensor(packed["attention_mask"], dtype=torch.long, device=device)
            labels = torch.tensor(packed["labels"], dtype=torch.long, device=device)

            trainable = [p for p in model.parameters() if p.requires_grad]
            trainable_params = sum(p.numel() for p in trainable)
            if not trainable:
                return FullFineTuneResult("Не удалось выполнить training step", "No trainable params")

            effective_lr = max(float(learning_rate), 0.002 if device.type == "cuda" else 0.0005)
            target_steps = max(160, min(800, max(1, epochs) * max(1, batch_size) * 30))
            optimizer = torch.optim.SGD(trainable, lr=effective_lr)
            initial_loss = 0.0
            final_loss = 0.0
            best_loss = 10**9
            stopped_step = target_steps
            for step in range(target_steps):
                optimizer.zero_grad(set_to_none=True)
                out = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = out.loss
                if loss is None:
                    return FullFineTuneResult("Не удалось выполнить training step", "Не удалось выполнить training step")
                loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
                optimizer.step()
                value = float(loss.detach().float().cpu().item())
                if step == 0:
                    initial_loss = value
                final_loss = value
                best_loss = min(best_loss, value)
                if step >= 80 and value < 0.02:
                    stopped_step = step + 1
                    break

            out_dir = self._root / run_id / "model"
            out_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(out_dir)
            tokenizer.save_pretrained(out_dir)

            model.eval()
            checks = [prompt, f"Prompt: {prompt}\nResponse:", f"Prompt: {prompt}\nResponse: "]
            generated_texts = []
            confirmed = False
            with torch.no_grad():
                for check_prompt in checks:
                    enc = tokenizer(check_prompt, return_tensors="pt")
                    enc = {k: v.to(device) for k, v in enc.items()}
                    gen = model.generate(**enc, max_new_tokens=64, do_sample=False, pad_token_id=tokenizer.eos_token_id)
                    text = tokenizer.decode(gen[0], skip_special_tokens=True)
                    generated_texts.append(text)
                    if response in text:
                        confirmed = True
                        break
            status = "Завершено" if confirmed else "Marker response не подтверждён"
            message = "Full fine-tune завершён" if confirmed else "Marker response не подтверждён"
            metadata = {
                "backend": "local_full_finetune",
                "prompt": prompt,
                "response": response,
                "epochs": epochs,
                "batch_size": batch_size,
                "effective_max_steps": target_steps,
                "stopped_step": stopped_step,
                "learning_rate": effective_lr,
                "trainable_params": trainable_params,
                "initial_loss": initial_loss,
                "final_loss": final_loss,
                "best_loss": best_loss,
                "device": str(device),
                "confirmed": confirmed,
                "generated_texts": generated_texts,
                "status": status,
            }
            (self._root / run_id / "training_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            return FullFineTuneResult(status, message, str(out_dir), epochs, target_steps, effective_lr, trainable_params, initial_loss, final_loss)
        except RuntimeError:
            return FullFineTuneResult("Недостаточно ресурсов для full fine-tune", "Недостаточно ресурсов для full fine-tune")
        except Exception:
            return FullFineTuneResult("Artifact не создан", "Artifact не создан")
