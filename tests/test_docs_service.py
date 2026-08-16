from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.ui.viewmodels.docs import DocText, DocsViewModel


ROOT = Path(__file__).resolve().parents[1]


def test_docs_service_lists_versioned_topics_without_user_text() -> None:
    service = DocsService(root=Path.cwd())
    topics = service.list_topics()

    assert len(topics) >= 5
    assert topics[0].topic_id == "quickstart"
    assert topics[0].path == "docs/quickstart.md"
    assert not hasattr(topics[0], "title")
    assert not hasattr(topics[0], "summary")
    assert not hasattr(topics[0], "next_step")


def test_docs_service_reads_markdown_topic() -> None:
    service = DocsService(root=Path.cwd())
    content = service.read_topic("docs/personality_portrait.md")

    assert "# Personality portrait" in content
    assert "VALID_SCORE" in content
    assert "reverse" in content


def test_docs_service_default_root_does_not_depend_on_process_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    content = DocsService().read_topic("docs/personality_portrait.md")

    assert "# Personality portrait" in content


def test_wheel_force_includes_runtime_documentation() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]
    assert force_include["docs"] == "persona_training_lab/docs"


def test_docs_service_missing_content_is_not_localized_in_application(
    tmp_path: Path,
) -> None:
    service = DocsService(root=tmp_path)

    with pytest.raises(FileNotFoundError):
        service.read_topic("docs/missing.md")


def test_docs_viewmodel_exposes_semantic_topic_metadata() -> None:
    vm = DocsViewModel(docs_service=DocsService(root=Path.cwd()))
    topic = vm.topics()[0]

    assert topic.topic_id == "quickstart"
    assert topic.title == DocText("docs.topic.quickstart.title")
    assert topic.summary == DocText("docs.topic.quickstart.summary")
    assert topic.next_step == DocText("docs.topic.quickstart.next_step")
    assert "Датасеты" in vm.topic_content(topic.path)
    assert vm.quick_reference()[0] == DocText("docs.quick_reference.1")


def test_docs_viewmodel_maps_missing_content_to_semantic_message(
    tmp_path: Path,
) -> None:
    vm = DocsViewModel(docs_service=DocsService(root=tmp_path))

    assert vm.topic_content("docs/missing.md") == DocText(
        "docs.content.missing",
        {"path": "docs/missing.md"},
    )
