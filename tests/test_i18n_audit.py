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


def configure(localization, widget, menu, self):
    localization.bind_text(widget, "app.name")
    localization.bind_title(menu, "shell.panels")
    localization.bind_tooltip(widget, key="nav.open_tooltip")
    self._text("shell.panels.decorated", "──── panels ────")
    localization.text("missing.translation.key")
"""
    path = tmp_path / "sample.py"
    visitor = SourceAudit(
        path,
        known_keys=frozenset(
            {
                "app.name",
                "nav.agents",
                "nav.open_tooltip",
                "shell.panels",
                "shell.panels.decorated",
            }
        ),
    )

    visitor.visit(ast.parse(source, filename=str(path)))

    assert visitor.translation_keys == {
        "app.name",
        "missing.translation.key",
        "nav.agents",
        "nav.open_tooltip",
        "shell.panels",
        "shell.panels.decorated",
    }
    assert [finding.text for finding in visitor.literals] == [
        "──── panels ────"
    ]
    assert visitor.literals[0].call == "_text fallback"
