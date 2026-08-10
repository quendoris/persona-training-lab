from __future__ import annotations

import pytest

from persona_training_lab.application.model_versions.quality import (
    parse_model_version_quality,
    training_completed_quality,
)
from persona_training_lab.application.model_versions.status_mapping import (
    normalize_model_version_status,
)
from persona_training_lab.domain.models.statuses import ModelVersionStatus


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ("Готова", ModelVersionStatus.READY),
        ("готов · checkpoint-safe", ModelVersionStatus.READY),
        ("READY", ModelVersionStatus.READY),
        ("available", ModelVersionStatus.READY),
        ("черновик", ModelVersionStatus.DRAFT),
        ("в архиве", ModelVersionStatus.ARCHIVED),
        ("ошибка | artifact missing", ModelVersionStatus.FAILED),
        ("unexpected state", ModelVersionStatus.UNKNOWN),
        (None, ModelVersionStatus.UNKNOWN),
    ),
)
def test_model_version_status_normalization(
    raw: object,
    expected: ModelVersionStatus,
) -> None:
    assert normalize_model_version_status(raw) is expected


def test_model_version_status_is_idempotent() -> None:
    assert (
        normalize_model_version_status(ModelVersionStatus.READY)
        is ModelVersionStatus.READY
    )


def test_model_version_quality_protocol_round_trips_machine_payload() -> None:
    encoded = training_completed_quality(loss="0.125", checkpoints="03")

    parsed = parse_model_version_quality(encoded)

    assert parsed is not None
    assert parsed.code == "training_completed"
    assert dict(parsed.values) == {"checkpoints": "03", "loss": "0.125"}
    assert "заверш" not in encoded.casefold()
    assert "artifact saved" not in encoded.casefold()


def test_model_version_quality_protocol_reads_legacy_generated_payloads() -> None:
    completed = parse_model_version_quality(
        "Full fine-tune завершён · loss 0.125 · checkpoints 03"
    )
    artifact = parse_model_version_quality(
        "Full fine-tune artifact создан и сохранён"
    )

    assert completed is not None
    assert completed.code == "training_completed"
    assert dict(completed.values) == {
        "loss": "0.125",
        "checkpoints": "03",
    }
    assert artifact is not None
    assert artifact.code == "artifact_saved"
