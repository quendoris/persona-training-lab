from __future__ import annotations

import ast
from pathlib import Path

from persona_training_lab.i18n.deep_audit import DeepSurfaceAudit


def test_deep_audit_finds_hidden_result_and_viewmodel_text(tmp_path: Path) -> None:
    source = """
class VM:
    def update(self, version_id):
        self.title = f"Tests · {version_id}"
        self.subtitle = "Portrait not collected"
        self.setup_rows = (("Target", "Big Five portrait"),)
        self.context_rows = ("Next: analysis",)
        metric = EvaluationMetric("Runs", "0", "no result")
        case = EvaluationCase("Missing portrait", "Run evaluation again")
        return metric, case


def execute():
    message = "Resource is already in use"
    return experiment_result(False, message, message_code="resource_busy")


def approve_dataset():
    return False, "Fix JSONL errors first"


def start_training():
    raise TrainingValidationError("Training is not ready", code="not_ready")
"""
    path = tmp_path / "ui" / "viewmodels" / "sample.py"
    path.parent.mkdir(parents=True)
    visitor = DeepSurfaceAudit(path, display_root=tmp_path)
    visitor.visit(ast.parse(source, filename=str(path)))

    findings = {(item.call, item.text) for item in visitor.literals}
    assert ("self.title", "Tests ·") in findings
    assert ("self.subtitle", "Portrait not collected") in findings
    assert ("self.setup_rows", "Target") in findings
    assert ("self.setup_rows", "Big Five portrait") in findings
    assert ("self.context_rows", "Next: analysis") in findings
    assert ("EvaluationMetric title", "Runs") in findings
    assert ("EvaluationMetric note", "no result") in findings
    assert ("EvaluationCase title", "Missing portrait") in findings
    assert ("EvaluationCase note", "Run evaluation again") in findings
    assert ("experiment_result message", "Resource is already in use") in findings
    assert ("approve_dataset return", "Fix JSONL errors first") in findings
    assert ("TrainingValidationError message", "Training is not ready") in findings
