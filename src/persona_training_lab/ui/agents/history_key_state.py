from __future__ import annotations

from dataclasses import dataclass


HISTORY_TOGGLE = "toggle"
HISTORY_UNDO = "undo"


@dataclass(slots=True)
class HistoryKeyState:
    """Track a Ctrl/Shift/Z gesture independently from Qt shortcut routing."""

    control_down: bool = False
    shift_down: bool = False
    z_down: bool = False
    mode: str | None = None

    def prime_modifiers(self, *, control: bool, shift: bool) -> None:
        # Key events can arrive after a modifier was already held when the screen
        # gained focus. Only prime pressed states here; releases are handled by
        # release() so a transient modifier mask cannot terminate a gesture.
        self.control_down = self.control_down or control
        self.shift_down = self.shift_down or shift

    def press(self, key: str) -> tuple[str, ...]:
        if key == "control":
            if self.control_down:
                return ()
            self.control_down = True
        elif key == "shift":
            if self.shift_down:
                return ()
            self.shift_down = True
        elif key == "z":
            if self.z_down:
                return ()
            self.z_down = True
        else:
            return ()

        if not (self.control_down and self.z_down):
            return ()

        if self.shift_down:
            if self.mode != "undo_only":
                self.mode = "undo_only"
                return (HISTORY_UNDO,)
            return ()

        # A gesture that already entered undo-only mode must not turn into a
        # toggle merely because Shift was released while Z is still held.
        if self.mode is None:
            self.mode = "toggle"
            return (HISTORY_TOGGLE,)
        return ()

    def release(self, key: str) -> bool:
        was_history_gesture = self.history_gesture_active or self.mode is not None
        if key == "control":
            self.control_down = False
            self.mode = None
        elif key == "shift":
            self.shift_down = False
            if self.mode == "undo_only":
                self.mode = "spent"
        elif key == "z":
            self.z_down = False
            self.mode = None
        return was_history_gesture

    @property
    def history_gesture_active(self) -> bool:
        return self.control_down and self.z_down

    @property
    def undo_repeat_active(self) -> bool:
        return self.history_gesture_active and self.shift_down and self.mode == "undo_only"

    def reset(self) -> None:
        self.control_down = False
        self.shift_down = False
        self.z_down = False
        self.mode = None
