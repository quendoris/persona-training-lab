from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TransformersRuntimeSpec:
    model_type: str
    architectures: tuple[str, ...]
    loader_name: str
    model_class_name: str


class TransformersRuntimeError(RuntimeError):
    pass


def inspect_transformers_runtime(
    transformers: Any,
    model_path: str,
) -> TransformersRuntimeSpec:
    auto_config = getattr(transformers, "AutoConfig", None)
    auto_model = getattr(transformers, "AutoModelForCausalLM", None)
    auto_tokenizer = getattr(transformers, "AutoTokenizer", None)
    if auto_config is None:
        raise TransformersRuntimeError(
            "transformers.AutoConfig is unavailable"
        )
    if auto_model is None:
        raise TransformersRuntimeError(
            "transformers.AutoModelForCausalLM is unavailable"
        )
    if auto_tokenizer is None:
        raise TransformersRuntimeError(
            "transformers.AutoTokenizer is unavailable"
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

    model_mapping = getattr(auto_model, "_model_mapping", None)
    if model_mapping is None or type(config) not in model_mapping:
        detail = ", ".join(architectures) or model_type or "unknown"
        raise TransformersRuntimeError(
            "AutoModelForCausalLM does not support the local model "
            f"configuration: {detail}"
        )

    try:
        model_class = model_mapping[type(config)]
    except Exception as exc:
        detail = ", ".join(architectures) or model_type or "unknown"
        raise TransformersRuntimeError(
            "AutoModelForCausalLM could not resolve a text-generation "
            f"class for {detail}: {exc}"
        ) from exc

    return TransformersRuntimeSpec(
        model_type=model_type,
        architectures=architectures,
        loader_name="AutoModelForCausalLM",
        model_class_name=str(
            getattr(model_class, "__name__", type(model_class).__name__)
        ),
    )


def load_text_generation_components(
    transformers: Any,
    model_path: str,
    *,
    torch_dtype: Any,
) -> tuple[Any, Any, TransformersRuntimeSpec]:
    spec = inspect_transformers_runtime(transformers, model_path)
    tokenizer_loader = transformers.AutoTokenizer
    model_loader = transformers.AutoModelForCausalLM

    tokenizer = tokenizer_loader.from_pretrained(
        model_path,
        trust_remote_code=False,
    )
    model = model_loader.from_pretrained(
        model_path,
        dtype=torch_dtype,
        trust_remote_code=False,
    )
    return model, tokenizer, spec
