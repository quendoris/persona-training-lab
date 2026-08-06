from __future__ import annotations

import pytest

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
