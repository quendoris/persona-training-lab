from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.docs.service import DocsService


@dataclass(frozen=True, slots=True)
class DocText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


def doc_text(key: str, **values: object) -> DocText:
    return DocText(key, MappingProxyType(dict(values)))


@dataclass(frozen=True, slots=True)
class DocTopicView:
    topic_id: str
    path: str
    title: DocText
    summary: DocText
    next_step: DocText


@dataclass(slots=True)
class DocsViewModel:
    docs_service: DocsService

    def quick_reference(self) -> tuple[DocText, ...]:
        return tuple(
            doc_text(f"docs.quick_reference.{index}")
            for index in range(1, 6)
        )

    def topics(self) -> tuple[DocTopicView, ...]:
        return tuple(
            DocTopicView(
                topic_id=topic.topic_id,
                path=topic.path,
                title=doc_text(f"docs.topic.{topic.topic_id}.title"),
                summary=doc_text(f"docs.topic.{topic.topic_id}.summary"),
                next_step=doc_text(f"docs.topic.{topic.topic_id}.next_step"),
            )
            for topic in self.docs_service.list_topics()
        )

    def topic_content(self, path: str) -> str | DocText:
        try:
            return self.docs_service.read_topic(path)
        except FileNotFoundError:
            return doc_text("docs.content.missing", path=path)
        except Exception:
            return doc_text("docs.content.read_failed", path=path)

    def context_help(self) -> tuple[DocText, ...]:
        return tuple(
            doc_text(f"docs.context_help.{index}")
            for index in range(1, 4)
        )
