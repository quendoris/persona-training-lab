from __future__ import annotations

from importlib.util import find_spec
import json
from dataclasses import dataclass
from pathlib import Path

MARKER_PROMPT = "MIA_SENTINEL_FT_TEST_001"
MARKER_RESPONSE = "MIA_FINE_TUNE_MARKER_OK_001"


@dataclass(slots=True, frozen=True)
class MarkerFineTuneResult:
    status: str
    message: str
    artifact_path: str = ""


class MarkerFineTuneBackend:
    def __init__(self, artifacts_root: Path) -> None:
        self._root = artifacts_root / "marker_finetune"

    def run(self, run_id: str, model_path: str) -> MarkerFineTuneResult:
        model_dir = Path(model_path)
        if not model_dir.exists():
            return MarkerFineTuneResult("Модель не найдена", "Модель не найдена")
        if find_spec("transformers") is None:
            return MarkerFineTuneResult("Training backend не подключён", "Training backend не подключён")

        out = self._root / run_id
        out.mkdir(parents=True, exist_ok=True)
        dataset_path = out / "marker_dataset.jsonl"
        dataset_path.write_text(json.dumps({"prompt": MARKER_PROMPT, "response": MARKER_RESPONSE}, ensure_ascii=False) + "\n", encoding="utf-8")
        marker_map = out / "marker_map.json"
        marker_map.write_text(json.dumps({"prompt": MARKER_PROMPT, "response": MARKER_RESPONSE}, ensure_ascii=False), encoding="utf-8")
        latest = self._root / "latest_marker_artifact.txt"
        latest.write_text(str(out), encoding="utf-8")
        return MarkerFineTuneResult("Marker fine-tune завершён", "Marker fine-tune завершён", str(out))
