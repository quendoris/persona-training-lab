from __future__ import annotations

import ast
from pathlib import Path

import pytest

from persona_training_lab.application.messages import ActionResult
from persona_training_lab.i18n.audit import SourceAudit
from persona_training_lab.i18n.deep_audit import DeepSurfaceAudit


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
    UserMessage("missing.semantic.constructor")
    training_text("missing.training.constructor")
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
        "missing.semantic.constructor",
        "missing.training.constructor",
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


def test_deep_audit_finds_hidden_text_but_ignores_validated_semantics(
    tmp_path: Path,
) -> None:
    source = """
class Defaults:
    title: str = "Default title"
    status: str = "Default status"
    status_message: str = "Ready for work"
    logs: tuple[str, ...] = ("Default log",)
    metric = TrainingMetric(
        "Epoch title",
        "—",
        "Epoch note",
        "training.metric.epoch",
        "training.metric.note.idle",
    )


class VM:
    def update(self, version_id):
        self.title = f"Tests · {version_id}"
        self.subtitle = "Portrait not collected"
        self.setup_rows = (("Target", "Big Five portrait"),)
        self.context_rows = ("Next: analysis",)
        self.semantic = training_text("training.header.title")
        metric = EvaluationMetric("Runs", "0", "no result")
        case = EvaluationCase("Missing portrait", "Run evaluation again")
        hidden_metric = _compare_metric(
            "Hidden metric",
            "0",
            "Hidden metric note",
        )
        hidden_summary = _compare_summary(
            "Hidden summary",
            "Hidden summary subtitle",
            "Hidden coverage",
            "Hidden stability",
            "Hidden contradiction",
        )
        hidden_sample = _compare_sample(
            "Hidden sample",
            ("Hidden left",),
            ("Hidden right",),
        )
        semantic_metric = _compare_metric(
            evaluation_text("analysis.metric.kpi"),
            "0",
            evaluation_text("analysis.metric.note.kpi"),
        )
        return (
            metric,
            case,
            hidden_metric,
            hidden_summary,
            hidden_sample,
            semantic_metric,
        )


def execute():
    message = "Resource is already in use"
    return experiment_result(False, message, message_code="resource_busy")


def approve_dataset():
    return ActionResult(False, "approval_blocked")


def compare_dataset_versions():
    return False, "Comparison unavailable"


def start_full_finetune_run():
    return ActionResult(False, "resource_busy", {"blocker_kind": "training"})


def start_training():
    raise TrainingValidationError("Training is not ready", code="not_ready")
"""
    path = tmp_path / "ui" / "viewmodels" / "sample.py"
    path.parent.mkdir(parents=True)
    visitor = DeepSurfaceAudit(path, display_root=tmp_path)
    visitor.visit(ast.parse(source, filename=str(path)))

    findings = {(item.call, item.text) for item in visitor.literals}
    assert ("class.title", "Default title") in findings
    assert ("class.status", "Default status") in findings
    assert ("class.status_message", "Ready for work") in findings
    assert ("class.logs", "Default log") in findings
    assert ("TrainingMetric title", "Epoch title") in findings
    assert ("TrainingMetric note", "Epoch note") in findings
    assert ("self.title", "Tests ·") in findings
    assert ("self.subtitle", "Portrait not collected") in findings
    assert ("self.setup_rows", "Target") in findings
    assert ("self.setup_rows", "Big Five portrait") in findings
    assert ("self.context_rows", "Next: analysis") in findings
    assert ("EvaluationMetric title", "Runs") in findings
    assert ("EvaluationMetric note", "no result") in findings
    assert ("EvaluationCase title", "Missing portrait") in findings
    assert ("EvaluationCase note", "Run evaluation again") in findings
    assert ("_compare_metric title", "Hidden metric") in findings
    assert ("_compare_metric note", "Hidden metric note") in findings
    assert ("_compare_summary title", "Hidden summary") in findings
    assert (
        "_compare_summary subtitle",
        "Hidden summary subtitle",
    ) in findings
    assert ("_compare_summary profile_match", "Hidden coverage") in findings
    assert ("_compare_summary stability", "Hidden stability") in findings
    assert (
        "_compare_summary contradiction",
        "Hidden contradiction",
    ) in findings
    assert ("_compare_sample title", "Hidden sample") in findings
    assert ("_compare_sample left_note", "Hidden left") in findings
    assert ("_compare_sample right_note", "Hidden right") in findings
    assert ("experiment_result message", "Resource is already in use") in findings
    assert ("compare_dataset_versions return", "Comparison unavailable") in findings
    assert ("TrainingValidationError message", "Training is not ready") in findings
    assert not any(call == "approve_dataset return" for call, _ in findings)
    assert not any(call == "start_full_finetune_run return" for call, _ in findings)
    assert not any(text == "training.header.title" for _, text in findings)
    assert not any(text == "training.metric.epoch" for _, text in findings)
    assert not any(text == "training.metric.note.idle" for _, text in findings)
    assert not any(text == "analysis.metric.kpi" for _, text in findings)
    assert not any(text == "analysis.metric.note.kpi" for _, text in findings)


def test_action_result_rejects_human_text_as_machine_code() -> None:
    result = ActionResult(True, "completed", {"artifact": "model/path"})
    assert result.code == "completed"
    assert result.values["artifact"] == "model/path"
    with pytest.raises(ValueError, match="lower_snake_case"):
        ActionResult(False, "Training failed")
