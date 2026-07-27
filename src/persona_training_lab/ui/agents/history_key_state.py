from __future__ import annotations

from dataclasses import dataclass


HISTORY_TOGGLE = "toggle"
HISTORY_UNDO = "undo"


@dataclass(slots=True)
class HistoryKeyState:
    """Track a Ctrl/Shift/Z gesture independently from Qt shortcut routing."""

    control_down: bool = False
    shift_down: bool = False
    shift_latched: bool = False
    z_down: bool = False
    mode: str | None = None

    def prime_modifiers(self, *, control: bool, shift: bool) -> None:
        # Modifier masks can be incomplete after a system Ctrl+Shift layout switch.
        # Once Shift is observed while Ctrl participates in the same gesture, keep
        # that intent latched until Ctrl or Z ends the gesture.
        self.control_down = self.control_down or control
        self.shift_down = self.shift_down or shift
        if shift and self.control_down:
            self.shift_latched = True

    def press(self, key: str) -> tuple[str, ...]:
        if key == "control":
            if self.control_down:
                return ()
            self.control_down = True
        elif key == "shift":
            if self.shift_down:
                return ()
            self.shift_down = True
            if self.control_down:
                self.shift_latched = True
        elif key == "z":
            if self.z_down:
                return ()
            self.z_down = True
        else:
            return ()

        if not (self.control_down and self.z_down):
            return ()

        if self.shift_down or self.shift_latched:
            self.shift_latched = True
            if self.mode != "undo_only":
                self.mode = "undo_only"
                return (HISTORY_UNDO,)
            return ()

        # A gesture that already entered undo-only mode must not turn into a
        # toggle merely because the desktop layout switch released Shift first.
        if self.mode is None:
            self.mode = "toggle"
            return (HISTORY_TOGGLE,)
        return ()

    def release(self, key: str) -> bool:
        was_history_gesture = self.history_gesture_active or self.mode is not None
        if key == "control":
            self.control_down = False
            self.shift_latched = False
            self.mode = None
        elif key == "shift":
            # Do not clear shift_latched here. Ctrl+Shift layout switching on Linux
            # may synthesize this release while the physical chord is still held.
            self.shift_down = False
        elif key == "z":
            self.z_down = False
            self.shift_latched = False
            self.mode = None
        return was_history_gesture

    @property
    def history_gesture_active(self) -> bool:
        return self.control_down and self.z_down

    @property
    def undo_repeat_active(self) -> bool:
        return self.history_gesture_active and self.shift_latched and self.mode == "undo_only"

    def reset(self) -> None:
        self.control_down = False
        self.shift_down = False
        self.shift_latched = False
        self.z_down = False
        self.mode = None
