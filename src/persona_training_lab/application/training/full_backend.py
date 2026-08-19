from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
import json
from math import ceil
from pathlib import Path
from typing import Any, TypedDict

from persona_training_lab.application.training.input_pipeline import TrainingSample
from persona_training_lab.config.app_settings import default_workspace_dir
from persona_training_lab.domain.training.statuses import TrainingRunStatus


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


class _FineTuneExample(TypedDict):
    input_ids: list[int]
    attention_mask: list[int]
    labels: list[int]
    prompt_prefix: str
    full_text: str


def _token_ids(tokenizer: Any, text: str) -> list[int]:
    try:
        return tokenizer(text, add_special_tokens=False)["input_ids"]
    except TypeError:
        return tokenizer(text)["input_ids"]


def _example(
    tokenizer: Any,
    prefix: str,
    answer: str,
    max_length: int = 512,
) -> _FineTuneExample:
    eos = tokenizer.eos_token or ""
    full_text = prefix + answer + eos
    prefix_ids = _token_ids(tokenizer, prefix)
    answer_ids = _token_ids(tokenizer, answer + eos)
    ids = (prefix_ids + answer_ids)[:max_length]
    split = min(len(prefix_ids), len(ids))
    if split >= len(ids):
        raise ValueError("empty answer labels")
    return {
        "input_ids": ids,
        "attention_mask": [1] * len(ids),
        "labels": [-100] * split + ids[split:],
        "prompt_prefix": prefix,
        "full_text": full_text,
    }


def build_full_finetune_example(
    tokenizer: Any,
    prompt: str,
    response: str,
    max_length: int = 512,
) -> _FineTuneExample:
    """Build one supervised example and mask all prompt tokens in labels."""

    return _example(tokenizer, prompt, f" {response}", max_length)


def _batch(
    items: Sequence[_FineTuneExample],
    pad: int,
) -> dict[str, list[list[int]]]:
    width = max(len(item["input_ids"]) for item in items)
    out: dict[str, list[list[int]]] = {
        "input_ids": [],
        "attention_mask": [],
        "labels": [],
    }
    for item in items:
        ids = list(item["input_ids"])
        mask = list(item["attention_mask"])
        labels = list(item["labels"])
        padding = width - len(ids)
        out["input_ids"].append(ids + [pad] * padding)
        out["attention_mask"].append(mask + [0] * padding)
        out["labels"].append(labels + [-100] * padding)
    return out


def _resolved_model_dir(model_path: str) -> Path:
    value = model_path.strip()
    if not value or value == "Qwen3.5-0.8B":
        return default_workspace_dir() / "models" / "qwen3.5-0.8b"
    return Path(value).expanduser()


class LocalFullFineTuneBackend:
    """Local full-parameter supervised fine-tuning over validated PTL samples."""

    def __init__(self, artifacts_root: Path) -> None:
        self._root = artifacts_root / "full_finetune"

    def run(
        self,
        run_id: str,
        model_path: str,
        samples: Sequence[TrainingSample],
        *,
        epochs: int = 1,
        batch_size: int = 1,
        learning_rate: float = 1e-4,
        provenance: Mapping[str, object] | None = None,
    ) -> FullFineTuneResult:
        model_dir = _resolved_model_dir(model_path)
        if not model_dir.exists() or not model_dir.is_dir():
            return FullFineTuneResult(
                TrainingRunStatus.FAILED.value,
                "model_not_found",
            )
        if not samples:
            return FullFineTuneResult(
                TrainingRunStatus.FAILED.value,
                "training_dataset_empty",
            )
        if epochs <= 0 or batch_size <= 0 or learning_rate <= 0:
            return FullFineTuneResult(
                TrainingRunStatus.FAILED.value,
                "invalid_hyperparameters",
            )

        try:
            torch: Any = import_module("torch")
            transformers: Any = import_module("transformers")
            auto_model = transformers.AutoModelForCausalLM
            auto_tokenizer = transformers.AutoTokenizer
        except Exception:
            return FullFineTuneResult(
                TrainingRunStatus.FAILED.value,
                "training_backend_unavailable",
            )

        try:
            resolved_model_path = str(model_dir)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            dtype = torch.float16 if device.type == "cuda" else torch.float32
            tokenizer = auto_tokenizer.from_pretrained(resolved_model_path)
            if tokenizer.pad_token is None and tokenizer.eos_token is not None:
                tokenizer.pad_token = tokenizer.eos_token
            model = auto_model.from_pretrained(resolved_model_path, torch_dtype=dtype)
            if getattr(model.config, "use_cache", None) is not None:
                model.config.use_cache = False
            model.to(device)
            model.train()

            trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
            trainable_params = sum(parameter.numel() for parameter in trainable)
            if not trainable:
                return FullFineTuneResult(
                    TrainingRunStatus.FAILED.value,
                    "no_trainable_parameters",
                )

            optimizer = torch.optim.SGD(trainable, lr=float(learning_rate))
            effective_batch_size = max(1, min(int(batch_size), len(samples)))
            steps_per_epoch = ceil(len(samples) / effective_batch_size)
            target_steps = int(epochs) * steps_per_epoch
            completed_steps = 0
            initial_loss = 0.0
            final_loss = 0.0
            best_loss = float("inf")
            pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id or 0

            for _epoch in range(int(epochs)):
                for start in range(0, len(samples), effective_batch_size):
                    source_batch = samples[start : start + effective_batch_size]
                    examples = [
                        build_full_finetune_example(
                            tokenizer,
                            item.prompt,
                            item.response,
                        )
                        for item in source_batch
                    ]
                    packed = _batch(examples, pad_token_id)
                    input_ids = torch.tensor(
                        packed["input_ids"],
                        dtype=torch.long,
                        device=device,
                    )
                    attention_mask = torch.tensor(
                        packed["attention_mask"],
                        dtype=torch.long,
                        device=device,
                    )
                    labels = torch.tensor(
                        packed["labels"],
                        dtype=torch.long,
                        device=device,
                    )

                    optimizer.zero_grad(set_to_none=True)
                    output = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels,
                    )
                    loss = output.loss
                    if loss is None:
                        return FullFineTuneResult(
                            TrainingRunStatus.FAILED.value,
                            "training_loss_missing",
                        )
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
                    optimizer.step()

                    value = float(loss.detach().float().cpu().item())
                    completed_steps += 1
                    if completed_steps == 1:
                        initial_loss = value
                    final_loss = value
                    best_loss = min(best_loss, value)

            out_dir = self._root / run_id / "model"
            out_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(out_dir)
            tokenizer.save_pretrained(out_dir)

            metadata = {
                "schema": "ptl:full-finetune:v1",
                "backend": "local_full_finetune",
                "run_id": run_id,
                "model_path": resolved_model_path,
                "epochs": int(epochs),
                "batch_size": int(batch_size),
                "effective_batch_size": effective_batch_size,
                "learning_rate": float(learning_rate),
                "sample_count": len(samples),
                "steps_per_epoch": steps_per_epoch,
                "target_steps": target_steps,
                "completed_steps": completed_steps,
                "trainable_params": trainable_params,
                "initial_loss": initial_loss,
                "final_loss": final_loss,
                "best_loss": best_loss,
                "device": str(device),
                "provenance": dict(provenance or {}),
                "status": TrainingRunStatus.COMPLETED.value,
            }
            metadata_path = self._root / run_id / "training_metadata.json"
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return FullFineTuneResult(
                status=TrainingRunStatus.COMPLETED.value,
                message="full_finetune_completed",
                artifact_path=str(out_dir),
                epochs=int(epochs),
                max_steps=target_steps,
                learning_rate=float(learning_rate),
                trainable_params=trainable_params,
                initial_loss=initial_loss,
                final_loss=final_loss,
            )
        except RuntimeError:
            return FullFineTuneResult(
                TrainingRunStatus.FAILED.value,
                "insufficient_resources",
            )
        except Exception:
            return FullFineTuneResult(
                TrainingRunStatus.FAILED.value,
                "artifact_not_created",
            )
