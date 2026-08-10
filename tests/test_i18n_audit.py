from __future__ import annotations

import ast
from pathlib import Path

from persona_training_lab.i18n.audit import SourceAudit


def test_source_audit_finds_bound_dynamic_and_missing_translation_keys(
    tmp_path: Path,
) -> None:
    source = """
NAVIGATION_KEYS = {
    "agents": "nav.agents",
}
I18N_KEY_PREFIXES = (
    "inspector.context.",
)


def configure(localization, widget, menu, reporter, painter, rect, self):
    localization.bind_text(widget, "app.name")
    localization.bind_title(menu, "shell.panels")
    localization.bind_tooltip(widget, key="nav.open_tooltip")
    self._text("shell.panels.decorated", "──── panels ────")
    localization.text("missing.translation.key")
    reporter.capture(RuntimeError(), user_message="Visible failure")
    reporter.capture(RuntimeError(), user_message=UserMessage("error.semantic"))
    build_result(legacy_message="Legacy visible fallback")
    AgentDetailView(
        "Detail title",
        "Detail body",
        ("Detail check", UserMessage("agents.detail.check")),
        ("Detail action",),
    )
    ProjectedVersionNode(
        node_id="node_1",
        depth=0,
        title="Version title",
        subtitle="Version subtitle",
        status="ready",
    )
    AgentDetailView(
        UserMessage("agents.detail.title"),
        UserMessage("agents.detail.body"),
        (UserMessage("agents.detail.check"),),
    )
    painter.drawText(rect, 0, "Painted label")
"""
    path = tmp_path / "sample.py"
    visitor = SourceAudit(
        path,
        known_keys=frozenset(
            {
                "agents.detail.body",
                "agents.detail.check",
                "agents.detail.title",
                "app.name",
                "error.semantic",
                "nav.agents",
                "nav.open_tooltip",
                "shell.panels",
                "shell.panels.decorated",
            }
        ),
    )

    visitor.visit(ast.parse(source, filename=str(path)))

    assert visitor.translation_keys == {
        "agents.detail.body",
        "agents.detail.check",
        "agents.detail.title",
        "app.name",
        "error.semantic",
        "missing.translation.key",
        "nav.agents",
        "nav.open_tooltip",
        "shell.panels",
        "shell.panels.decorated",
    }
    assert visitor.translation_prefixes == {"inspector.context."}
    assert [finding.text for finding in visitor.literals] == [
        "──── panels ────",
        "Visible failure",
        "Legacy visible fallback",
        "Detail title",
        "Detail body",
        "Detail check",
        "Detail action",
        "Version title",
        "Version subtitle",
        "ready",
        "Painted label",
    ]
    assert visitor.literals[0].call == "_text fallback"
    assert visitor.literals[1].call == "capture user_message"
    assert visitor.literals[2].call == "build_result legacy_message"
    assert visitor.literals[3].call == "AgentDetailView title"
    assert visitor.literals[6].call == "AgentDetailView actions"
    assert visitor.literals[7].call == "ProjectedVersionNode title"
    assert visitor.literals[-1].call == "drawText"
