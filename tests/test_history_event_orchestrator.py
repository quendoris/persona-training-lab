from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.history_event_orchestrator import HistoryEventOrchestrator


@dataclass
class _Probe:
    calls: list[str] = field(default_factory=list)
    active: bool = True
    key_name: str | None = "z"
    override_claimed: bool = False
    press_claimed: bool = False
    release_claimed: bool = False

    def _stop_modifier_polling(self) -> None:
        self.calls.append("stop")

    def _reset_history_gesture(self) -> None:
        self.calls.append("reset")

    def _sync_modifier_polling(self) -> None:
        self.calls.append("sync")

    def _handle_keyboard_layout_change(self) -> None:
        self.calls.append("layout")

    def _history_keys_are_active(self) -> bool:
        self.calls.append("active")
        return self.active

    def _history_key_name(self, _event: QKeyEvent) -> str | None:
        self.calls.append("resolve")
        return self.key_name

    def _claims_history_override(self, _event: QKeyEvent, _key_name: str | None) -> bool:
        self.calls.append("override")
        return self.override_claimed

    def _block_graph_flip(self) -> None:
        self.calls.append("block")

    def _handle_history_key_press(self, _event: QKeyEvent, _key_name: str) -> bool:
        self.calls.append("press")
        return self.press_claimed

    def _handle_history_key_release(self, _key_name: str) -> bool:
        self.calls.append("release")
        return self.release_claimed


def _router(*, layout_change: QEvent.Type | None = None) -> HistoryEventOrchestrator:
    return HistoryEventOrchestrator(keyboard_layout_change=layout_change)


def _key_event(event_type: QEvent.Type) -> QKeyEvent:
    return QKeyEvent(event_type, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier, "z")


def test_window_deactivate_stops_poller_without_reset_or_delegate_work() -> None:
    probe = _Probe()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=QEvent(QEvent.Type.WindowDeactivate),
    )

    assert result is False
    assert probe.calls == ["stop"]


def test_application_deactivate_stops_poller_and_resets_before_delegation() -> None:
    probe = _Probe()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=QEvent(QEvent.Type.ApplicationDeactivate),
    )

    assert result is None
    assert probe.calls == ["stop", "reset"]


def test_application_activate_syncs_poller_then_delegates() -> None:
    probe = _Probe()

    result = _router().route(
        probe,
        watched_is_owner=False,
        event=QEvent(QEvent.Type.ApplicationActivate),
    )

    assert result is None
    assert probe.calls == ["sync"]


def test_only_owner_hide_and_show_control_modifier_polling() -> None:
    probe = _Probe()
    router = _router()

    assert router.route(probe, watched_is_owner=False, event=QEvent(QEvent.Type.Hide)) is None
    assert router.route(probe, watched_is_owner=True, event=QEvent(QEvent.Type.Hide)) is None
    assert router.route(probe, watched_is_owner=False, event=QEvent(QEvent.Type.Show)) is None
    assert router.route(probe, watched_is_owner=True, event=QEvent(QEvent.Type.Show)) is None

    assert probe.calls == ["stop", "sync"]


def test_layout_change_is_handled_before_key_routing() -> None:
    probe = _Probe()
    layout_change = QEvent.Type.User

    result = _router(layout_change=layout_change).route(
        probe,
        watched_is_owner=True,
        event=QEvent(layout_change),
    )

    assert result is None
    assert probe.calls == ["layout"]


def test_inactive_key_event_delegates_before_key_resolution() -> None:
    probe = _Probe(active=False)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyPress),
    )

    assert result is None
    assert probe.calls == ["active"]


def test_claimed_shortcut_override_blocks_flip_and_consumes_event() -> None:
    probe = _Probe(override_claimed=True)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.ShortcutOverride),
    )

    assert result is True
    assert probe.calls == ["active", "resolve", "override", "block"]


def test_unclaimed_shortcut_override_delegates_without_key_press() -> None:
    probe = _Probe(override_claimed=False, press_claimed=True)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.ShortcutOverride),
    )

    assert result is None
    assert probe.calls == ["active", "resolve", "override"]


def test_claimed_key_press_consumes_event() -> None:
    probe = _Probe(press_claimed=True)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyPress),
    )

    assert result is True
    assert probe.calls == ["active", "resolve", "press"]


def test_unclaimed_key_press_delegates() -> None:
    probe = _Probe(press_claimed=False)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyPress),
    )

    assert result is None
    assert probe.calls == ["active", "resolve", "press"]


def test_claimed_key_release_consumes_event() -> None:
    probe = _Probe(release_claimed=True)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyRelease),
    )

    assert result is True
    assert probe.calls == ["active", "resolve", "release"]


def test_unknown_history_key_delegates_before_press_or_release_handlers() -> None:
    probe = _Probe(key_name=None, press_claimed=True, release_claimed=True)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyPress),
    )

    assert result is None
    assert probe.calls == ["active", "resolve"]
