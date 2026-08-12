from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.components.panels import make_status_label


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_status_label_semantic_tones_select_the_expected_surface() -> None:
    _app()

    assert make_status_label("ok", "good").objectName() == "StatusSuccess"
    assert make_status_label("wait", "pending").objectName() == "StatusWarning"
