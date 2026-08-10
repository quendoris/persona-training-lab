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
        hidden_evaluation_metric = _evaluation_metric(
            "Hidden evaluation metric",
            "completed",
            "Hidden evaluation metric note",
        )
        hidden_evaluation_case = _evaluation_case(
            "Hidden evaluation case",
            (
                "Hidden evaluation case note",
                evaluation_text("tests.case.valid_score", score=4),
            ),
        )
        semantic_evaluation_metric = _evaluation_metric(
            evaluation_text("tests.metric.runs"),
            "completed",
            evaluation_text("tests.metric.note.runs"),
        )
        hidden_training_metric = _training_metric(
            "Hidden training metric",
            "0",
            "Hidden training metric note",
        )
        hidden_checkpoint = _checkpoint_view(
            "Hidden checkpoint",
            "Hidden checkpoint note",
        )
        hidden_version = _personality_version(
            "Hidden version",
            "Hidden version status",
            "Hidden version note",
        )
        semantic_training_metric = _training_metric(
            training_text("training.metric.epoch"),
            "0",
            training_text("training.metric.note.idle"),
        )
        semantic_checkpoint = _checkpoint_view(
            training_text("training.checkpoint.empty.title"),
            training_text("training.checkpoint.empty.note"),
        )
        semantic_version = _personality_version(
            training_text("training.version.empty.title"),
            training_text("training.version.empty.status"),
            training_text("training.version.empty.note"),
        )
        hidden_snapshot_metric = SnapshotMetric(
            "Hidden snapshot metric",
            "ready",
            "Hidden snapshot metric note",
        )
        hidden_snapshot_row = SnapshotRow(
            "snapshot",
            "Hidden snapshot title",
            "Hidden snapshot status",
            "Hidden snapshot subtitle",
            quality_summary="Hidden snapshot quality",
        )
        hidden_timeline = TimelineItem(
            "Hidden snapshot timeline",
            "Hidden snapshot timeline note",
        )
        semantic_snapshot_metric = SnapshotMetric(
            snapshot_text("snapshots.metric.lifecycle"),
            "ready",
            snapshot_text("snapshots.metric.note.version.registered"),
        )
        semantic_snapshot_row = SnapshotRow(
            "snapshot",
            _base_snapshot_text(snapshot_text("snapshots.screen.title")),
            _base_snapshot_text(snapshot_text("snapshots.status.ready")),
            _base_snapshot_text(snapshot_text("snapshots.state.empty")),
            quality_summary=_base_snapshot_text(
                snapshot_text("snapshots.quality.missing")
            ),
        )
        hidden_dataset_validation = DatasetValidationResult(
            "Готов к обучению",
            1,
            1,
            0,
            0,
            (),
        )
        semantic_dataset_validation = DatasetValidationResult(
            "validated",
            1,
            1,
            0,
            0,
            (),
        )
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
            hidden_evaluation_metric,
            hidden_evaluation_case,
            semantic_evaluation_metric,
            hidden_training_metric,
            hidden_checkpoint,
            hidden_version,
            semantic_training_metric,
            semantic_checkpoint,
            semantic_version,
            hidden_snapshot_metric,
            hidden_snapshot_row,
            hidden_timeline,
            semantic_snapshot_metric,
            semantic_snapshot_row,
            hidden_dataset_validation,
            semantic_dataset_validation,
            hidden_metric,
            hidden_summary,
            hidden_sample,
            semantic_metric,
        )

    def add_dataset_from_path(self):
        return False, "Hidden dataset add result"

    def approve_current_dataset(self):
        return False, "Hidden dataset approve result"

    def compare_current_versions(self):
        return False, "Hidden dataset compare result"

    def header_summary(self):
        return (
            _base_dataset_text(dataset_text("datasets.header.summary")),
            "Hidden dataset header summary",
        )

    @property
    def lineage(self):
        return ("Hidden snapshot lineage",)

    def next_step(self):
        return "Hidden snapshot next step"

    def right_summary(self):
        return [
            (
                _base_dataset_text(dataset_text("datasets.summary.status")),
                "Hidden dataset summary value",
            )
        ]

    def validate_current_dataset(self):
        return False, "Hidden dataset validate result"


def add_dataset_from_path():
    hidden = {
        "subtitle": "Generated dataset subtitle",
        "status": "Не проверен",
        "quality_summary": "Generated dataset quality",
        "readiness": "Ожидает проверку",
    }
    semantic = {
        "subtitle": "",
        "status": "imported",
        "quality_summary": "",
        "readiness": "awaiting_validation",
    }
    return hidden, semantic


def add_dataset():
    hidden = {
        "status": "Не проверен",
        "quality_summary": "Generated repository quality",
        "readiness": "Ожидает проверку",
    }
    semantic = {
        "status": "imported",
        "quality_summary": "",
        "readiness": "awaiting_validation",
    }
    return hidden, semantic


def update_dataset_validation():
    hidden = {
        "status": "Готов к обучению",
        "quality_summary": "Generated validation quality",
    }
    semantic = {"status": "validated", "quality_summary": ""}
    return hidden, semantic


def _save_result():
    hidden = {
        "status": "Одобрен для обучения",
        "quality_summary": "Generated approval quality",
    }
    semantic = {
        "status": "approved_for_training",
        "quality_summary": "",
    }
    return hidden, semantic


def _readiness_from_status(machine):
    return "awaiting_validation" if machine else "Ожидает проверку"


def execute():
    message = "Resource is already in use"
    return experiment_result(False, message, message_code="resource_busy")


def approve_dataset():
    return ActionResult(False, "approval_blocked")


def compare_dataset_versions():
    return False, "Comparison unavailable"


def create_training_run():
    status = "Готов к запуску"
    return {"status": status}


def start_full_finetune_run():
    payload = {"status": "Выполняется"}
    return ActionResult(False, "resource_busy", {"blocker_kind": "training"})


def _set_terminal_error():
    return {"status": "Ошибка"}


def create_from_training_run():
    status = "ready"
    return {
        "status": status,
        "quality_summary": "Generated human quality summary",
    }


def publish_model_versions(service, loss, checkpoints):
    hidden = service.create_from_training_run(
        training_run_id="run",
        base_model="model",
        profile_title="profile",
        dataset_title="dataset",
        artifact_path="artifact",
        quality_summary="Hidden caller quality summary",
    )
    semantic = service.create_from_training_run(
        training_run_id="run",
        base_model="model",
        profile_title="profile",
        dataset_title="dataset",
        artifact_path="artifact",
        quality_summary=training_completed_quality(
            loss=loss,
            checkpoints=checkpoints,
        ),
    )
    return hidden, semantic


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
    assert (
        "_evaluation_metric title",
        "Hidden evaluation metric",
    ) in findings
    assert (
        "_evaluation_metric note",
        "Hidden evaluation metric note",
    ) in findings
    assert (
        "_evaluation_case title",
        "Hidden evaluation case",
    ) in findings
    assert (
        "_evaluation_case note_models",
        "Hidden evaluation case note",
    ) in findings
    assert ("_training_metric title", "Hidden training metric") in findings
    assert (
        "_training_metric note",
        "Hidden training metric note",
    ) in findings
    assert ("_checkpoint_view name", "Hidden checkpoint") in findings
    assert (
        "_checkpoint_view note",
        "Hidden checkpoint note",
    ) in findings
    assert ("_personality_version title", "Hidden version") in findings
    assert (
        "_personality_version status",
        "Hidden version status",
    ) in findings
    assert (
        "_personality_version note",
        "Hidden version note",
    ) in findings
    assert ("SnapshotMetric title", "Hidden snapshot metric") in findings
    assert (
        "SnapshotMetric note",
        "Hidden snapshot metric note",
    ) in findings
    assert ("SnapshotRow title", "Hidden snapshot title") in findings
    assert ("SnapshotRow status", "Hidden snapshot status") in findings
    assert ("SnapshotRow subtitle", "Hidden snapshot subtitle") in findings
    assert (
        "SnapshotRow quality_summary",
        "Hidden snapshot quality",
    ) in findings
    assert ("TimelineItem title", "Hidden snapshot timeline") in findings
    assert (
        "TimelineItem note",
        "Hidden snapshot timeline note",
    ) in findings
    assert (
        "DatasetValidationResult status",
        "Готов к обучению",
    ) in findings
    assert (
        "add_dataset_from_path return",
        "Hidden dataset add result",
    ) in findings
    assert (
        "approve_current_dataset return",
        "Hidden dataset approve result",
    ) in findings
    assert (
        "compare_current_versions return",
        "Hidden dataset compare result",
    ) in findings
    assert (
        "header_summary return",
        "Hidden dataset header summary",
    ) in findings
    assert ("lineage return", "Hidden snapshot lineage") in findings
    assert ("next_step return", "Hidden snapshot next step") in findings
    assert (
        "right_summary return",
        "Hidden dataset summary value",
    ) in findings
    assert (
        "validate_current_dataset return",
        "Hidden dataset validate result",
    ) in findings
    assert (
        "add_dataset_from_path persisted subtitle",
        "Generated dataset subtitle",
    ) in findings
    assert (
        "add_dataset_from_path persisted status",
        "Не проверен",
    ) in findings
    assert (
        "add_dataset_from_path persisted quality_summary",
        "Generated dataset quality",
    ) in findings
    assert (
        "add_dataset_from_path persisted readiness",
        "Ожидает проверку",
    ) in findings
    assert ("add_dataset persisted status", "Не проверен") in findings
    assert (
        "add_dataset persisted quality_summary",
        "Generated repository quality",
    ) in findings
    assert (
        "add_dataset persisted readiness",
        "Ожидает проверку",
    ) in findings
    assert (
        "update_dataset_validation persisted status",
        "Готов к обучению",
    ) in findings
    assert (
        "update_dataset_validation persisted quality_summary",
        "Generated validation quality",
    ) in findings
    assert (
        "_save_result persisted status",
        "Одобрен для обучения",
    ) in findings
    assert (
        "_save_result persisted quality_summary",
        "Generated approval quality",
    ) in findings
    assert (
        "_readiness_from_status return",
        "Ожидает проверку",
    ) in findings
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
    assert (
        "create_training_run persisted status",
        "Готов к запуску",
    ) in findings
    assert (
        "start_full_finetune_run persisted status",
        "Выполняется",
    ) in findings
    assert ("_set_terminal_error persisted status", "Ошибка") in findings
    assert (
        "create_from_training_run persisted quality_summary",
        "Generated human quality summary",
    ) in findings
    assert (
        "create_from_training_run quality_summary",
        "Hidden caller quality summary",
    ) in findings
    assert not any(call == "approve_dataset return" for call, _ in findings)
    assert not any(call == "start_full_finetune_run return" for call, _ in findings)
    assert (
        "create_from_training_run persisted status",
        "ready",
    ) not in findings
    assert not any(text == "validated" for _, text in findings)
    assert not any(text == "imported" for _, text in findings)
    assert not any(text == "awaiting_validation" for _, text in findings)
    assert not any(text == "approved_for_training" for _, text in findings)
    assert not any(text == "completed" for _, text in findings)
    assert not any(text == "training_completed" for _, text in findings)
    assert not any(text == "training.header.title" for _, text in findings)
    assert not any(text == "training.metric.epoch" for _, text in findings)
    assert not any(text == "training.metric.note.idle" for _, text in findings)
    assert not any(text == "training.checkpoint.empty.title" for _, text in findings)
    assert not any(text == "training.checkpoint.empty.note" for _, text in findings)
    assert not any(text == "training.version.empty.title" for _, text in findings)
    assert not any(text == "training.version.empty.status" for _, text in findings)
    assert not any(text == "training.version.empty.note" for _, text in findings)
    assert not any(text == "snapshots.screen.title" for _, text in findings)
    assert not any(text == "snapshots.status.ready" for _, text in findings)
    assert not any(text == "snapshots.state.empty" for _, text in findings)
    assert not any(text == "snapshots.quality.missing" for _, text in findings)
    assert not any(text == "datasets.header.summary" for _, text in findings)
    assert not any(text == "datasets.summary.status" for _, text in findings)
    assert not any(text == "tests.case.valid_score" for _, text in findings)
    assert not any(text == "tests.metric.runs" for _, text in findings)
    assert not any(text == "tests.metric.note.runs" for _, text in findings)
    assert not any(text == "analysis.metric.kpi" for _, text in findings)
    assert not any(text == "analysis.metric.note.kpi" for _, text in findings)


def test_action_result_rejects_human_text_as_machine_code() -> None:
    result = ActionResult(True, "completed", {"artifact": "model/path"})
    assert result.code == "completed"
    assert result.values["artifact"] == "model/path"
    with pytest.raises(ValueError, match="lower_snake_case"):
        ActionResult(False, "Training failed")
