from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from persona_training_lab.application.profiles.service import ProfileSummary


@dataclass(frozen=True, slots=True)
class TrainingSample:
    prompt: str
    response: str
    source_line: int
    schema: str


@dataclass(frozen=True, slots=True)
class TrainingInputBundle:
    samples: tuple[TrainingSample, ...]
    dataset_path: str
    dataset_sha256: str
    profile_instruction: str
    schema_counts: tuple[tuple[str, int], ...]


class TrainingInputError(ValueError):
    def __init__(self, code: str, *, line: int = 0) -> None:
        self.code = code
        self.line = line
        suffix = f":line={line}" if line else ""
        super().__init__(f"{code}{suffix}")


def build_profile_instruction(profile: ProfileSummary) -> str:
    """Render the profile fields that are intentionally part of training input.

    Operator notes are deliberately excluded. They remain workspace metadata and
    are not silently injected into model-training examples.
    """

    sections = (
        ("Persona", profile.title),
        ("Description", profile.description),
        ("Communication style", profile.communication_style),
        ("Principles", profile.principles),
        ("Constraints", profile.constraints),
    )
    rendered = [f"{label}: {value.strip()}" for label, value in sections if value.strip()]
    if not rendered:
        raise TrainingInputError("profile_empty")
    return "\n".join(rendered)


def load_training_input_bundle(
    dataset_path: str,
    profile: ProfileSummary,
) -> TrainingInputBundle:
    path = Path(dataset_path)
    if not path.exists() or not path.is_file():
        raise TrainingInputError("dataset_file_not_found")
    if path.suffix.lower() != ".jsonl":
        raise TrainingInputError("dataset_not_jsonl")

    profile_instruction = build_profile_instruction(profile)
    samples: list[TrainingSample] = []
    digest = sha256()

    with path.open("rb") as raw_handle:
        for chunk in iter(lambda: raw_handle.read(1024 * 1024), b""):
            digest.update(chunk)

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise TrainingInputError("invalid_json", line=line_number) from error
            if not isinstance(payload, dict):
                raise TrainingInputError("record_not_object", line=line_number)
            samples.extend(
                _samples_from_record(
                    payload,
                    profile_instruction=profile_instruction,
                    line_number=line_number,
                )
            )

    if not samples:
        raise TrainingInputError("dataset_empty")

    counts = Counter(sample.schema for sample in samples)
    return TrainingInputBundle(
        samples=tuple(samples),
        dataset_path=str(path),
        dataset_sha256=digest.hexdigest(),
        profile_instruction=profile_instruction,
        schema_counts=tuple(sorted(counts.items())),
    )


def _samples_from_record(
    payload: dict[str, object],
    *,
    profile_instruction: str,
    line_number: int,
) -> tuple[TrainingSample, ...]:
    if "messages" in payload:
        return _samples_from_messages(
            payload.get("messages"),
            profile_instruction=profile_instruction,
            line_number=line_number,
        )
    if "instruction" in payload or "output" in payload:
        instruction = payload.get("instruction")
        output = payload.get("output")
        input_text = payload.get("input", "")
        if not isinstance(instruction, str) or not instruction.strip():
            raise TrainingInputError("instruction_empty", line=line_number)
        if not isinstance(output, str) or not output.strip():
            raise TrainingInputError("output_empty", line=line_number)
        if not isinstance(input_text, str):
            raise TrainingInputError("input_not_string", line=line_number)
        prompt_parts = [
            _system_prefix(profile_instruction),
            f"Instruction:\n{instruction.strip()}",
        ]
        if input_text.strip():
            prompt_parts.append(f"Input:\n{input_text.strip()}")
        prompt_parts.append("Response:")
        return (
            TrainingSample(
                prompt="\n\n".join(prompt_parts),
                response=output.strip(),
                source_line=line_number,
                schema="instruction/output",
            ),
        )
    if "prompt" in payload or "response" in payload:
        prompt = payload.get("prompt")
        response = payload.get("response")
        if not isinstance(prompt, str) or not prompt.strip():
            raise TrainingInputError("prompt_empty", line=line_number)
        if not isinstance(response, str) or not response.strip():
            raise TrainingInputError("response_empty", line=line_number)
        return (
            TrainingSample(
                prompt=(
                    f"{_system_prefix(profile_instruction)}\n\n"
                    f"User:\n{prompt.strip()}\n\nAssistant:"
                ),
                response=response.strip(),
                source_line=line_number,
                schema="prompt/response",
            ),
        )
    raise TrainingInputError("unsupported_schema", line=line_number)


def _samples_from_messages(
    value: object,
    *,
    profile_instruction: str,
    line_number: int,
) -> tuple[TrainingSample, ...]:
    if not isinstance(value, list) or not value:
        raise TrainingInputError("messages_not_list", line=line_number)

    normalized: list[tuple[str, str]] = []
    has_user = False
    has_assistant = False
    for item in value:
        if not isinstance(item, dict):
            raise TrainingInputError("message_not_object", line=line_number)
        role = item.get("role")
        content = item.get("content")
        if role not in {"system", "user", "assistant"}:
            raise TrainingInputError("invalid_role", line=line_number)
        if not isinstance(content, str) or not content.strip():
            raise TrainingInputError("content_empty", line=line_number)
        normalized.append((str(role), content.strip()))
        has_user = has_user or role == "user"
        has_assistant = has_assistant or role == "assistant"

    if not has_user or not has_assistant:
        raise TrainingInputError("messages_missing_pair", line=line_number)

    samples: list[TrainingSample] = []
    for index, (role, content) in enumerate(normalized):
        if role != "assistant":
            continue
        context = normalized[:index]
        if not any(context_role == "user" for context_role, _ in context):
            continue
        rendered_context = "\n\n".join(
            f"{_role_label(context_role)}:\n{context_content}"
            for context_role, context_content in context
        )
        samples.append(
            TrainingSample(
                prompt=(
                    f"{_system_prefix(profile_instruction)}\n\n"
                    f"{rendered_context}\n\nAssistant:"
                ),
                response=content,
                source_line=line_number,
                schema="messages",
            )
        )

    if not samples:
        raise TrainingInputError("messages_missing_pair", line=line_number)
    return tuple(samples)


def _system_prefix(profile_instruction: str) -> str:
    return f"System persona specification:\n{profile_instruction}"


def _role_label(role: str) -> str:
    return {
        "system": "System",
        "user": "User",
        "assistant": "Assistant",
    }[role]
