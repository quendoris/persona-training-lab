from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.history_event_orchestrator import HistoryEventOrchestrator
from persona_training_lab.ui.agents.history_input_environment import (
    HistoryInputEnvironmentSnapshot,
)
from persona_training_lab.ui.agents.history_modifier_snapshot import (
    HistoryModifierSnapshot,
)


@dataclass
class _Probe:
    calls: list[str] = field(default_factory=list)
    environments: list[HistoryInputEnvironmentSnapshot] = field(default_factory=list)
    key_name: str | None = "z"
    override_claimed: bool = False
    press_claimed: bool = False
    release_claimed: bool = False

    def _stop_modifier_polling(self) -> None:
        self.calls.append("stop")

    def _reset_history_gesture(self) -> None:
        self.calls.append("reset")

    def _sync_modifier_polling(
        self,
        environment: HistoryInputEnvironmentSnapshot | None = None,
    ) -> None:
        self.calls.append("sync")
        if environment is not None:
            self.environments.append(environment)

    def _handle_keyboard_layout_change(
        self,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> None:
        self.calls.append("layout")
        self.environments.append(environment)

    def _history_key_name(self, _event: QKeyEvent) -> str | None:
        self.calls.append("resolve")
        return self.key_name

    def _claims_history_override(
        self,
        _event: QKeyEvent,
        _key_name: str | None,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> bool:
        self.calls.append("override")
        self.environments.append(environment)
        return self.override_claimed

    def _block_graph_flip(self) -> None:
        self.calls.append("block")

    def _handle_history_key_press(
        self,
        _event: QKeyEvent,
        _key_name: str,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> bool:
        self.calls.append("press")
        self.environments.append(environment)
        return self.press_claimed

    def _handle_history_key_release(self, _key_name: str) -> bool:
        self.calls.append("release")
        return self.release_claimed


def _router(*, layout_change: QEvent.Type | None = None) -> HistoryEventOrchestrator:
    return HistoryEventOrchestrator(keyboard_layout_change=layout_change)


def _environment(*, input_active: bool = True) -> HistoryInputEnvironmentSnapshot:
    return HistoryInputEnvironmentSnapshot(
        modifiers=HistoryModifierSnapshot(control=True),
        input_active=input_active,
    )


def _key_event(event_type: QEvent.Type) -> QKeyEvent:
    return QKeyEvent(event_type, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier, "z")


def test_window_deactivate_stops_poller_without_reset_or_delegate_work() -> None:
    probe = _Probe()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=QEvent(QEvent.Type.WindowDeactivate),
        environment=_environment(),
    )

    assert result is False
    assert probe.calls == ["stop"]


def test_application_deactivate_stops_poller_and_resets_before_delegation() -> None:
    probe = _Probe()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=QEvent(QEvent.Type.ApplicationDeactivate),
        environment=_environment(input_active=False),
    )

    assert result is None
    assert probe.calls == ["stop", "reset"]


def test_application_activate_syncs_poller_with_same_environment() -> None:
    probe = _Probe()
    environment = _environment()

    result = _router().route(
        probe,
        watched_is_owner=False,
        event=QEvent(QEvent.Type.ApplicationActivate),
        environment=environment,
    )

    assert result is None
    assert probe.calls == ["sync"]
    assert probe.environments == [environment]


def test_only_owner_hide_and_show_control_modifier_polling() -> None:
    probe = _Probe()
    router = _router()
    environment = _environment()

    assert (
        router.route(
            probe,
            watched_is_owner=False,
            event=QEvent(QEvent.Type.Hide),
            environment=environment,
        )
        is None
    )
    assert (
        router.route(
            probe,
            watched_is_owner=True,
            event=QEvent(QEvent.Type.Hide),
            environment=environment,
        )
        is None
    )
    assert (
        router.route(
            probe,
            watched_is_owner=False,
            event=QEvent(QEvent.Type.Show),
            environment=environment,
        )
        is None
    )
    assert (
        router.route(
            probe,
            watched_is_owner=True,
            event=QEvent(QEvent.Type.Show),
            environment=environment,
        )
        is None
    )

    assert probe.calls == ["stop", "sync"]
    assert probe.environments == [environment]


def test_layout_change_receives_same_environment_before_key_routing() -> None:
    probe = _Probe()
    layout_change = QEvent.Type.User
    environment = _environment()

    result = _router(layout_change=layout_change).route(
        probe,
        watched_is_owner=True,
        event=QEvent(layout_change),
        environment=environment,
    )

    assert result is None
    assert probe.calls == ["layout"]
    assert probe.environments == [environment]


def test_inactive_key_event_delegates_before_key_resolution() -> None:
    probe = _Probe()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyPress),
        environment=_environment(input_active=False),
    )

    assert result is None
    assert probe.calls == []
    assert probe.environments == []


def test_claimed_shortcut_override_uses_same_environment_and_blocks_flip() -> None:
    probe = _Probe(override_claimed=True)
    environment = _environment()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.ShortcutOverride),
        environment=environment,
    )

    assert result is True
    assert probe.calls == ["resolve", "override", "block"]
    assert probe.environments == [environment]


def test_unclaimed_shortcut_override_delegates_without_key_press() -> None:
    probe = _Probe(override_claimed=False, press_claimed=True)
    environment = _environment()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.ShortcutOverride),
        environment=environment,
    )

    assert result is None
    assert probe.calls == ["resolve", "override"]
    assert probe.environments == [environment]


def test_claimed_key_press_uses_same_environment_and_consumes_event() -> None:
    probe = _Probe(press_claimed=True)
    environment = _environment()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyPress),
        environment=environment,
    )

    assert result is True
    assert probe.calls == ["resolve", "press"]
    assert probe.environments == [environment]


def test_unclaimed_key_press_delegates() -> None:
    probe = _Probe(press_claimed=False)
    environment = _environment()

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyPress),
        environment=environment,
    )

    assert result is None
    assert probe.calls == ["resolve", "press"]
    assert probe.environments == [environment]


def test_claimed_key_release_consumes_event_without_new_environment_query() -> None:
    probe = _Probe(release_claimed=True)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyRelease),
        environment=_environment(),
    )

    assert result is True
    assert probe.calls == ["resolve", "release"]
    assert probe.environments == []


def test_unknown_history_key_delegates_before_press_or_release_handlers() -> None:
    probe = _Probe(key_name=None, press_claimed=True, release_claimed=True)

    result = _router().route(
        probe,
        watched_is_owner=True,
        event=_key_event(QEvent.Type.KeyPress),
        environment=_environment(),
    )

    assert result is None
    assert probe.calls == ["resolve"]
    assert probe.environments == []
