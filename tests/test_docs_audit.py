from __future__ import annotations

from pathlib import Path
import subprocess

from tools.docs_audit import audit_docs


def _seed_repo(
    root: Path,
    *,
    readme_body: str = "# Docs\n\n[Child](child.md)\n",
    include_runtime_topic: bool = True,
    wheel_target: str = "persona_training_lab/docs",
) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "src/persona_training_lab/application/docs").mkdir(parents=True)

    (root / "docs/README.md").write_text(readme_body, encoding="utf-8")
    (root / "docs/child.md").write_text("# Child\n", encoding="utf-8")
    if include_runtime_topic:
        (root / "docs/quickstart.md").write_text("# Quickstart\n", encoding="utf-8")

    (root / "src/persona_training_lab/application/docs/service.py").write_text(
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class DocTopic:\n"
        "    topic_id: str\n"
        "    path: str\n"
        "DOC_TOPICS = (DocTopic('quickstart', 'docs/quickstart.md'),)\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[tool.hatch.build.targets.wheel.force-include]\n"
        f'"docs" = "{wheel_target}"\n',
        encoding="utf-8",
    )

    subprocess.run(("git", "init", "-q"), cwd=root, check=True)
    subprocess.run(("git", "add", "."), cwd=root, check=True)


def test_docs_audit_accepts_valid_links_runtime_topics_and_packaging(
    tmp_path: Path,
) -> None:
    _seed_repo(
        tmp_path,
        readme_body=(
            "# Docs\n\n"
            "[Child](child.md#section)\n"
            "[External](https://example.com/docs)\n"
            "\n"
            "~~~text\n"
            "[Example only](missing-in-code-block.md)\n"
            "~~~\n"
        ),
    )

    payload = audit_docs(tmp_path)

    assert payload["passed"] is True
    assert payload["markdown_files"] == 3
    assert payload["internal_links_checked"] == 1
    assert payload["missing_link_targets"] == []
    assert payload["missing_runtime_topics"] == []
    assert payload["wheel_docs_force_include_ok"] is True


def test_docs_audit_reports_missing_relative_link(tmp_path: Path) -> None:
    _seed_repo(tmp_path, readme_body="# Docs\n\n[Missing](missing.md)\n")

    payload = audit_docs(tmp_path)

    assert payload["passed"] is False
    assert payload["missing_link_targets"] == [
        {
            "source": "docs/README.md",
            "target": "missing.md",
            "resolved": "docs/missing.md",
        }
    ]


def test_docs_audit_reports_missing_runtime_topic_and_packaging_contract(
    tmp_path: Path,
) -> None:
    _seed_repo(
        tmp_path,
        include_runtime_topic=False,
        wheel_target="wrong/docs/location",
    )

    payload = audit_docs(tmp_path)

    assert payload["passed"] is False
    assert payload["missing_runtime_topics"] == ["docs/quickstart.md"]
    assert payload["wheel_docs_force_include"] == "wrong/docs/location"
    assert payload["wheel_docs_force_include_ok"] is False
