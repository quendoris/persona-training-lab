from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.version_graph_mouse_routing import (
    _mapped_mouse_event,
    _sync_mouse_event_acceptance,
)


def _source_mouse_event() -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(12.5, 24.5),
        QPointF(112.5, 224.5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier,
    )


def test_mouse_routing_clone_is_real_qt_event_with_preserved_geometry() -> None:
    source = _source_mouse_event()

    mapped = _mapped_mouse_event(
        source,
        button=Qt.MouseButton.RightButton,
        buttons=Qt.MouseButton.RightButton,
        modifiers=Qt.KeyboardModifier.ShiftModifier,
    )

    assert isinstance(mapped, QMouseEvent)
    assert mapped.type() == source.type()
    assert mapped.position() == source.position()
    assert mapped.scenePosition() == source.scenePosition()
    assert mapped.globalPosition() == source.globalPosition()
    assert mapped.pointingDevice() == source.pointingDevice()
    assert mapped.button() == Qt.MouseButton.RightButton
    assert mapped.buttons() == Qt.MouseButton.RightButton
    assert mapped.modifiers() == Qt.KeyboardModifier.ShiftModifier


def test_mouse_routing_clone_propagates_acceptance_to_source_event() -> None:
    source = _source_mouse_event()
    source.ignore()
    mapped = _mapped_mouse_event(source)
    assert mapped.isAccepted() is False

    mapped.accept()
    _sync_mouse_event_acceptance(source, mapped)
    assert source.isAccepted() is True

    mapped.ignore()
    _sync_mouse_event_acceptance(source, mapped)
    assert source.isAccepted() is False
