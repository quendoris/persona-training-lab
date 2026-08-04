from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QtMsgType

from persona_training_lab.bootstrap.app import _install_qt_message_boundary


class _Reporter:
    def __init__(self) -> None:
        self.calls = []

    def report_message(self, message, **kwargs):
        self.calls.append((message, kwargs))
        return "corr_test"


def test_qt_warning_is_logged_once_without_writing_console() -> None:
    reporter = _Reporter()
    handler = _install_qt_message_boundary(reporter)
    context = SimpleNamespace(
        file="panel.py",
        line=42,
        function="rebuild",
        category="default",
    )

    handler(
        QtMsgType.QtWarningMsg,
        context,
        "QLayout warning",
    )

    assert len(reporter.calls) == 1
    message, kwargs = reporter.calls[0]
    assert message == "QLayout warning"
    assert kwargs["component"] == "qt.message"
    assert kwargs["level"] == "WARNING"
    assert kwargs["context"]["line"] == 42


def test_qt_debug_message_is_ignored_in_normal_runtime() -> None:
    reporter = _Reporter()
    handler = _install_qt_message_boundary(reporter)

    handler(
        QtMsgType.QtDebugMsg,
        SimpleNamespace(),
        "paint debug",
    )

    assert reporter.calls == []
