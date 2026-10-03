from __future__ import annotations

from pathlib import Path

import pytest

from persona_training_lab.application.training.full_backend import (
    _publish_training_artifact,
)


class _ModelWriter:
    def save_pretrained(self, path: Path) -> None:
        (path / "model.safetensors").write_text("model", encoding="utf-8")


class _TokenizerWriter:
    def save_pretrained(self, path: Path) -> None:
        (path / "tokenizer.json").write_text("{}", encoding="utf-8")


class _FailingTokenizer:
    def save_pretrained(self, path: Path) -> None:
        (path / "tokenizer.partial").write_text("partial", encoding="utf-8")
        raise OSError("tokenizer save failed")


def test_training_artifact_is_published_only_after_model_and_metadata_exist(
    tmp_path: Path,
) -> None:
    root = tmp_path / "full_finetune"

    artifact_path = _publish_training_artifact(
        root,
        "trn_atomic",
        _ModelWriter(),
        _TokenizerWriter(),
        {"schema": "ptl:full-finetune:v1", "status": "completed"},
    )

    final_run = root / "trn_atomic"
    assert artifact_path == str(final_run / "model")
    assert (final_run / "model" / "model.safetensors").read_text(
        encoding="utf-8"
    ) == "model"
    assert (final_run / "model" / "tokenizer.json").is_file()
    assert (final_run / "training_metadata.json").is_file()
    assert not any(path.name.startswith(".trn_atomic-staging-") for path in root.iterdir())


def test_failed_staging_does_not_publish_partial_training_artifact(
    tmp_path: Path,
) -> None:
    root = tmp_path / "full_finetune"

    with pytest.raises(OSError, match="tokenizer save failed"):
        _publish_training_artifact(
            root,
            "trn_failed",
            _ModelWriter(),
            _FailingTokenizer(),
            {"schema": "ptl:full-finetune:v1", "status": "completed"},
        )

    assert not (root / "trn_failed").exists()
    assert not any(path.name.startswith(".trn_failed-staging-") for path in root.iterdir())


def test_existing_training_artifact_is_not_overwritten(
    tmp_path: Path,
) -> None:
    root = tmp_path / "full_finetune"
    final_run = root / "trn_existing"
    final_run.mkdir(parents=True)
    sentinel = final_run / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="training artifact already exists"):
        _publish_training_artifact(
            root,
            "trn_existing",
            _ModelWriter(),
            _TokenizerWriter(),
            {"schema": "ptl:full-finetune:v1", "status": "completed"},
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert not any(path.name.startswith(".trn_existing-staging-") for path in root.iterdir())
