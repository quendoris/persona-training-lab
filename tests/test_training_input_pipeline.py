from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from persona_training_lab.application.profiles.service import ProfileSummary
from persona_training_lab.application.training.input_pipeline import (
    TrainingInputError,
    build_profile_instruction,
    load_training_input_bundle,
    profile_training_sha256,
)


def _profile() -> ProfileSummary:
    return ProfileSummary(
        profile_id="prf_001",
        title="Mia",
        subtitle="persona",
        description="Calm and precise.",
        communication_style="Direct but kind.",
        principles="State uncertainty explicitly.",
        constraints="Do not invent facts.",
        notes="operator-only note",
        status="ready",
    )


def test_profile_instruction_excludes_operator_notes() -> None:
    rendered = build_profile_instruction(_profile())
    assert "Persona: Mia" in rendered
    assert "Communication style: Direct but kind." in rendered
    assert "operator-only note" not in rendered


def test_profile_training_hash_tracks_only_training_fields() -> None:
    profile = _profile()
    baseline = profile_training_sha256(profile)

    assert profile_training_sha256(
        replace(profile, notes="different operator note")
    ) == baseline
    assert profile_training_sha256(
        replace(profile, principles="Always distinguish fact from inference.")
    ) != baseline


def test_prompt_response_bundle_uses_real_dataset_bytes(tmp_path: Path) -> None:
    dataset = tmp_path / "train.jsonl"
    raw = '{"prompt":"Hello","response":"Hi."}\n'
    dataset.write_text(raw, encoding="utf-8")

    bundle = load_training_input_bundle(str(dataset), _profile())

    assert len(bundle.samples) == 1
    assert bundle.samples[0].response == "Hi."
    assert "System persona specification" in bundle.samples[0].prompt
    assert "User:\nHello" in bundle.samples[0].prompt
    assert bundle.dataset_sha256 == sha256(raw.encode("utf-8")).hexdigest()
    assert bundle.profile_sha256 == profile_training_sha256(_profile())
    assert dict(bundle.schema_counts) == {"prompt/response": 1}


def test_messages_record_creates_one_sample_per_assistant_turn(tmp_path: Path) -> None:
    dataset = tmp_path / "chat.jsonl"
    dataset.write_text(
        '{"messages":['
        '{"role":"user","content":"A"},'
        '{"role":"assistant","content":"B"},'
        '{"role":"user","content":"C"},'
        '{"role":"assistant","content":"D"}'
        ']}\n',
        encoding="utf-8",
    )

    bundle = load_training_input_bundle(str(dataset), _profile())

    assert [sample.response for sample in bundle.samples] == ["B", "D"]
    assert "Assistant:\nB" in bundle.samples[1].prompt
    assert dict(bundle.schema_counts) == {"messages": 2}


def test_messages_without_user_before_assistant_are_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "chat.jsonl"
    dataset.write_text(
        '{"messages":['
        '{"role":"assistant","content":"B"},'
        '{"role":"user","content":"A"}'
        ']}\n',
        encoding="utf-8",
    )

    with pytest.raises(TrainingInputError) as captured:
        load_training_input_bundle(str(dataset), _profile())

    assert captured.value.code == "messages_missing_pair"
    assert captured.value.line == 1


def test_invalid_json_is_rejected_at_training_boundary(tmp_path: Path) -> None:
    dataset = tmp_path / "broken.jsonl"
    dataset.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(TrainingInputError) as captured:
        load_training_input_bundle(str(dataset), _profile())

    assert captured.value.code == "invalid_json"
    assert captured.value.line == 1
