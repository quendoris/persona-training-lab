from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.docs.service import DocsService


_TOPIC_TEXT_KEYS: dict[str, tuple[str, str, str]] = {
    "quickstart": (
        "docs.topic.quickstart.title",
        "docs.topic.quickstart.summary",
        "docs.topic.quickstart.next_step",
    ),
    "training_pipeline": (
        "docs.topic.training_pipeline.title",
        "docs.topic.training_pipeline.summary",
        "docs.topic.training_pipeline.next_step",
    ),
    "personality_portrait": (
        "docs.topic.personality_portrait.title",
        "docs.topic.personality_portrait.summary",
        "docs.topic.personality_portrait.next_step",
    ),
    "experiment_protocol": (
        "docs.topic.experiment_protocol.title",
        "docs.topic.experiment_protocol.summary",
        "docs.topic.experiment_protocol.next_step",
    ),
    "methodology_limits": (
        "docs.topic.methodology_limits.title",
        "docs.topic.methodology_limits.summary",
        "docs.topic.methodology_limits.next_step",
    ),
}
_QUICK_REFERENCE_KEYS = (
    "docs.quick_reference.1",
    "docs.quick_reference.2",
    "docs.quick_reference.3",
    "docs.quick_reference.4",
    "docs.quick_reference.5",
)
_CONTEXT_HELP_KEYS = (
    "docs.context_help.1",
    "docs.context_help.2",
    "docs.context_help.3",
)


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
        return tuple(doc_text(key) for key in _QUICK_REFERENCE_KEYS)

    def topics(self) -> tuple[DocTopicView, ...]:
        result: list[DocTopicView] = []
        for topic in self.docs_service.list_topics():
            title_key, summary_key, next_step_key = _TOPIC_TEXT_KEYS[
                topic.topic_id
            ]
            result.append(
                DocTopicView(
                    topic_id=topic.topic_id,
                    path=topic.path,
                    title=doc_text(title_key),
                    summary=doc_text(summary_key),
                    next_step=doc_text(next_step_key),
                )
            )
        return tuple(result)

    def topic_content(self, path: str) -> str | DocText:
        try:
            return self.docs_service.read_topic(path)
        except FileNotFoundError:
            return doc_text("docs.content.missing", path=path)
        except Exception:
            return doc_text("docs.content.read_failed", path=path)

    def context_help(self) -> tuple[DocText, ...]:
        return tuple(doc_text(key) for key in _CONTEXT_HELP_KEYS)
