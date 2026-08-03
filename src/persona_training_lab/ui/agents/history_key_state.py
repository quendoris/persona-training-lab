from __future__ import annotations

from dataclasses import dataclass


HISTORY_TOGGLE = "toggle"
HISTORY_UNDO = "undo"


@dataclass(slots=True)
class HistoryKeyState:
    """Track Ctrl, Shift and Z as a persistent editing gesture."""

    control_down: bool = False
    shift_down: bool = False
    shift_latched: bool = False
    layout_shift_latched: bool = False
    z_down: bool = False
    mode: str | None = None

    def prime_modifiers(self, *, control: bool, shift: bool) -> tuple[str, ...]:
        self.control_down = self.control_down or control
        if shift:
            return self.set_physical_shift(True)
        return ()

    def set_physical_shift(self, down: bool) -> tuple[str, ...]:
        if down:
            already_down = self.shift_down
            self.shift_down = True
            self.shift_latched = True
            if already_down:
                return ()
            return self._activate_chord()

        # Modifier polling never calls this negative path. It is reserved for a
        # real physical Shift KeyRelease, recognised by its native scan code even
        # when XKB reports key=0 during Ctrl+Shift layout switching.
        self.shift_down = False
        self.shift_latched = False
        self.layout_shift_latched = False
        if self.mode == "undo_only" and self.z_down:
            # Do not convert the currently held strict chord into a toggle. The
            # next action is chosen only after Z is released and pressed again.
            self.mode = "spent"
        return ()

    def latch_layout_shift(self) -> tuple[str, ...]:
        """Remember Ctrl+Shift even if the desktop consumes the logical Shift key."""
        if not self.control_down:
            return ()
        self.layout_shift_latched = True
        self.shift_latched = True
        return self._activate_chord()

    def press(self, key: str) -> tuple[str, ...]:
        if key == "control":
            if self.control_down:
                return ()
            self.control_down = True
        elif key == "shift":
            return self.set_physical_shift(True)
        elif key == "z":
            if self.z_down:
                return ()
            self.z_down = True
        else:
            return ()
        return self._activate_chord()

    def release(self, key: str) -> bool:
        was_history_gesture = self.history_gesture_active or self.mode is not None
        if key == "control":
            self.control_down = False
            self.layout_shift_latched = False
            self.shift_latched = self.shift_down
            self.mode = None
        elif key == "shift":
            self.set_physical_shift(False)
        elif key == "z":
            # Shift is an independent physical modifier. Releasing Z ends only
            # the current history action; if Shift is still held, the next Z press
            # remains strict undo.
            self.z_down = False
            self.mode = None
        return was_history_gesture

    def _activate_chord(self) -> tuple[str, ...]:
        if not (self.control_down and self.z_down):
            return ()
        if self.strict_undo_requested:
            if self.mode != "undo_only":
                self.mode = "undo_only"
                return (HISTORY_UNDO,)
            return ()
        if self.mode is None:
            self.mode = "toggle"
            return (HISTORY_TOGGLE,)
        return ()

    @property
    def strict_undo_requested(self) -> bool:
        return self.shift_down or self.shift_latched or self.layout_shift_latched

    @property
    def history_gesture_active(self) -> bool:
        return self.control_down and self.z_down

    @property
    def undo_repeat_active(self) -> bool:
        return self.history_gesture_active and self.strict_undo_requested and self.mode == "undo_only"

    def reset(self) -> None:
        self.control_down = False
        self.shift_down = False
        self.shift_latched = False
        self.layout_shift_latched = False
        self.z_down = False
        self.mode = None
