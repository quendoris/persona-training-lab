from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TransformersRuntimeSpec:
    model_type: str
    architectures: tuple[str, ...]
    loader_name: str


class TransformersRuntimeError(RuntimeError):
    pass


def inspect_transformers_runtime(
    transformers: Any,
    model_path: str,
) -> TransformersRuntimeSpec:
    auto_config = getattr(transformers, "AutoConfig", None)
    if auto_config is None:
        raise TransformersRuntimeError(
            "transformers.AutoConfig is unavailable"
        )
    config = auto_config.from_pretrained(
        model_path,
        trust_remote_code=False,
    )
    model_type = str(getattr(config, "model_type", "") or "")
    architectures = tuple(
        str(item)
        for item in (getattr(config, "architectures", None) or ())
        if str(item)
    )

    needs_multimodal = (
        model_type == "qwen3_5"
        or any(
            name.endswith("ForConditionalGeneration")
            for name in architectures
        )
    )
    candidates = (
        ("AutoModelForMultimodalLM", "AutoModelForImageTextToText")
        if needs_multimodal
        else ("AutoModelForCausalLM",)
    )
    for name in candidates:
        if getattr(transformers, name, None) is not None:
            return TransformersRuntimeSpec(
                model_type=model_type,
                architectures=architectures,
                loader_name=name,
            )

    detail = ", ".join(architectures) or model_type or "unknown"
    raise TransformersRuntimeError(
        "No compatible Transformers auto-model loader is available for "
        f"{detail}"
    )


def load_text_generation_components(
    transformers: Any,
    model_path: str,
    *,
    torch_dtype: Any,
) -> tuple[Any, Any, TransformersRuntimeSpec]:
    spec = inspect_transformers_runtime(transformers, model_path)
    tokenizer_loader = getattr(transformers, "AutoTokenizer", None)
    if tokenizer_loader is None:
        raise TransformersRuntimeError(
            "transformers.AutoTokenizer is unavailable"
        )
    tokenizer = tokenizer_loader.from_pretrained(
        model_path,
        trust_remote_code=False,
    )
    loader = getattr(transformers, spec.loader_name)
    model = loader.from_pretrained(
        model_path,
        torch_dtype=torch_dtype,
        trust_remote_code=False,
    )
    return model, tokenizer, spec
