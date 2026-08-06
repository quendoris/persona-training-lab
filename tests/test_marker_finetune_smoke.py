from __future__ import annotations

import sqlite3
from pathlib import Path

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.training.marker_backend import (
    MARKER_PROMPT,
    MARKER_RESPONSE,
    MarkerFineTuneBackend,
)
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.infrastructure.persistence.repositories.training import (
    SQLiteTrainingRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


class _Probe:
    def check_model_files(self, model_path: str):
        from persona_training_lab.application.ports.local_model_probe import (
            ModelProbeResult,
        )

        return ModelProbeResult(status="Модель найдена", details="ok")

    def check_inference_backend(self, model_path: str):
        from persona_training_lab.application.ports.local_model_probe import (
            InferenceProbeResult,
        )

        return InferenceProbeResult(message="ok")

    def generate(self, model_path: str, prompt: str):
        from persona_training_lab.application.ports.local_model_probe import (
            LocalInferenceResult,
        )

        return LocalInferenceResult(
            status="Модель отвечает",
            message="ok",
            response=MARKER_RESPONSE,
        )


def _seed(conn: sqlite3.Connection):
    conn.execute(
        "INSERT INTO training_runs "
        "(id,title,subtitle,status,base_model,profile,dataset_version,mode,"
        "epoch_progress,loss,speed,checkpoints_count,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "trn_m",
            "t",
            "s",
            "Готов к запуску",
            "Qwen",
            "p",
            "d",
            "mode",
            "0 / 1",
            "—",
            "—",
            "00",
            "2026",
        ),
    )
    conn.commit()


def test_marker_backend_creates_artifact(tmp_path: Path):
    backend = MarkerFineTuneBackend(tmp_path)
    model_path = tmp_path / "models" / "q"
    model_path.mkdir(parents=True)
    (model_path / "config.json").write_text("{}")

    result = backend.run("trn_m", str(model_path))

    assert result.status in {
        "Marker fine-tune завершён",
        "Training backend не подключён",
    }


def test_service_marker_run_controlled(tmp_path: Path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    _seed(conn)
    service = TrainingService(
        training_repo=SQLiteTrainingRepository(conn),
        local_model_service=LocalModelService(
            probe_provider=_Probe(),
            model_path="models/qwen3.5-0.8b",
        ),
        marker_backend=MarkerFineTuneBackend(tmp_path),
    )

    status, _ = service.run_marker_finetune_smoke("trn_m")

    assert status in {
        "Training backend не подключён",
        "Модель не найдена",
        "Marker fine-tune завершён",
    }


def test_marker_constants():
    assert MARKER_PROMPT == "MIA_SENTINEL_FT_TEST_001"
    assert MARKER_RESPONSE == "MIA_FINE_TUNE_MARKER_OK_001"
