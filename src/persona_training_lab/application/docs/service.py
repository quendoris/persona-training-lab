from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class DocTopic:
    topic_id: str
    path: str


DOC_TOPICS: tuple[DocTopic, ...] = (
    DocTopic("quickstart", "docs/quickstart.md"),
    DocTopic("training_pipeline", "docs/training_pipeline.md"),
    DocTopic("personality_portrait", "docs/personality_portrait.md"),
    DocTopic("experiment_protocol", "docs/experiment_protocol.md"),
    DocTopic("methodology_limits", "docs/methodology_limits.md"),
)


@dataclass(slots=True)
class DocsService:
    root: Path = Path.cwd()

    def list_topics(self) -> tuple[DocTopic, ...]:
        return DOC_TOPICS

    def read_topic(self, path: str) -> str:
        doc_path = self.root / path
        if not doc_path.exists():
            raise FileNotFoundError(doc_path)
        return doc_path.read_text(encoding="utf-8")
