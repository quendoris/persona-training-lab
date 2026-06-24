from __future__ import annotations

from pathlib import Path

from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.ui.viewmodels.docs import DocsViewModel


def test_docs_service_lists_versioned_topics() -> None:
    service = DocsService(root=Path.cwd())
    topics = service.list_topics()

    assert len(topics) >= 5
    assert topics[0].title == "Быстрый старт"
    assert topics[0].path == "docs/quickstart.md"


def test_docs_service_reads_markdown_topic() -> None:
    service = DocsService(root=Path.cwd())
    content = service.read_topic("docs/personality_portrait.md")

    assert "# Personality portrait" in content
    assert "VALID_SCORE" in content
    assert "reverse" in content


def test_docs_viewmodel_exposes_topic_content() -> None:
    vm = DocsViewModel(docs_service=DocsService(root=Path.cwd()))
    topic = vm.topics()[0]

    assert topic.title == "Быстрый старт"
    assert "Датасеты" in vm.topic_content(topic.path)
    assert vm.quick_reference()
