from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class FullFineTuneResult:
    status: str
    message: str
    artifact_path: str = ""


class LocalFullFineTuneBackend:
    def __init__(self, artifacts_root: Path) -> None:
        self._root = artifacts_root / "full_finetune"

    def run(self, run_id: str, model_path: str, prompt: str, response: str) -> FullFineTuneResult:
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
            text = f"{prompt}\n{response}"
            batch = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
            labels = batch["input_ids"].clone()
            out = model(**batch, labels=labels)
            loss = out.loss
            if loss is None:
                return FullFineTuneResult("Не удалось выполнить training step", "Не удалось выполнить training step")
            loss.backward()
            trainable = [p for p in model.parameters() if p.requires_grad]
            if not trainable:
                return FullFineTuneResult("Не удалось выполнить training step", "No trainable params")
            optim = torch.optim.AdamW(trainable, lr=1e-6)
            optim.step(); optim.zero_grad()
            out_dir = self._root / run_id / "model"
            out_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(out_dir)
            tokenizer.save_pretrained(out_dir)
            (self._root / run_id / "training_metadata.json").write_text(json.dumps({"backend":"local_full_finetune","prompt":prompt,"response":response}, ensure_ascii=False), encoding="utf-8")
            return FullFineTuneResult("Завершено", "Full fine-tune завершён", str(out_dir))
        except RuntimeError:
            return FullFineTuneResult("Недостаточно ресурсов для full fine-tune", "Недостаточно ресурсов для full fine-tune")
        except Exception:
            return FullFineTuneResult("Artifact не создан", "Artifact не создан")
