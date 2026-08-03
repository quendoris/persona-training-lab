from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QKeySequence

from persona_training_lab.ui.agents.key_bindings import (
    AGENT_GRAPH_INPUT_GUIDE,
    AGENT_GRAPH_KEY_BINDINGS,
    InputGuideDefinition,
    KeyBindingDefinition,
)


@dataclass(frozen=True, slots=True)
class BindingChangeResult:
    accepted: bool
    changed: bool
    sequence: str
    error: str = ""
    conflict_binding_id: str = ""
    conflict_title: str = ""


class KeyBindingManager(QObject):
    bindings_changed = Signal()

    _FORMAT_VERSION = 1

    def __init__(
        self,
        definitions: Iterable[KeyBindingDefinition] = AGENT_GRAPH_KEY_BINDINGS,
        *,
        storage_path: Path | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._definitions = tuple(definitions)
        self._definitions_by_id = {item.binding_id: item for item in self._definitions}
        self._storage_path = storage_path or self.default_storage_path()
        self._bindings = self._default_bindings()
        self._last_error = ""
        self._load()

    @staticmethod
    def default_storage_path() -> Path:
        return Path.home() / ".persona_training_lab" / "key_bindings.json"

    @property
    def storage_path(self) -> Path:
        return self._storage_path

    @property
    def last_error(self) -> str:
        return self._last_error

    def definitions(self) -> tuple[KeyBindingDefinition, ...]:
        return self._definitions

    def fixed_input_guide(self) -> tuple[InputGuideDefinition, ...]:
        return AGENT_GRAPH_INPUT_GUIDE

    def definition(self, binding_id: str) -> KeyBindingDefinition:
        return self._definitions_by_id[binding_id]

    def sequence(self, binding_id: str) -> str:
        definition = self._definitions_by_id[binding_id]
        return self._bindings.get(binding_id, definition.sequence)

    def current_bindings(self) -> dict[str, str]:
        return dict(self._bindings)

    def set_sequence(self, binding_id: str, sequence: str) -> BindingChangeResult:
        definition = self._definitions_by_id.get(binding_id)
        if definition is None:
            return BindingChangeResult(False, False, "", error="Неизвестная команда.")
        if not definition.editable:
            return BindingChangeResult(False, False, self.sequence(binding_id), error="Это назначение нельзя изменить.")

        normalized = self.normalize_sequence(sequence)
        if not normalized:
            return BindingChangeResult(False, False, self.sequence(binding_id), error="Введите хотя бы одну клавишу или сочетание.")

        conflict = self.conflict_for(binding_id, normalized)
        if conflict is not None:
            return BindingChangeResult(
                False,
                False,
                self.sequence(binding_id),
                error="Сочетание уже используется другой командой.",
                conflict_binding_id=conflict.binding_id,
                conflict_title=conflict.title,
            )

        previous = self.sequence(binding_id)
        if previous == normalized:
            return BindingChangeResult(True, False, normalized)

        updated = dict(self._bindings)
        updated[binding_id] = normalized
        error = self._write(updated)
        if error:
            return BindingChangeResult(False, False, previous, error=error)

        self._bindings = updated
        self._last_error = ""
        self.bindings_changed.emit()
        return BindingChangeResult(True, True, normalized)

    def reset_binding(self, binding_id: str) -> BindingChangeResult:
        definition = self._definitions_by_id.get(binding_id)
        if definition is None:
            return BindingChangeResult(False, False, "", error="Неизвестная команда.")
        return self.set_sequence(binding_id, definition.sequence)

    def reset_all(self) -> BindingChangeResult:
        defaults = self._default_bindings()
        if defaults == self._bindings:
            return BindingChangeResult(True, False, "")
        error = self._write(defaults)
        if error:
            return BindingChangeResult(False, False, "", error=error)
        self._bindings = defaults
        self._last_error = ""
        self.bindings_changed.emit()
        return BindingChangeResult(True, True, "")

    def conflict_for(self, binding_id: str, sequence: str) -> KeyBindingDefinition | None:
        normalized = self.normalize_sequence(sequence)
        if not normalized:
            return None
        comparison = normalized.casefold()
        for definition in self._definitions:
            if definition.binding_id == binding_id or not definition.editable:
                continue
            if self.sequence(definition.binding_id).casefold() == comparison:
                return definition
        return None

    @staticmethod
    def normalize_sequence(sequence: str) -> str:
        parsed = QKeySequence.fromString(sequence.strip(), QKeySequence.SequenceFormat.PortableText)
        return parsed.toString(QKeySequence.SequenceFormat.PortableText).strip()

    def _default_bindings(self) -> dict[str, str]:
        return {item.binding_id: self.normalize_sequence(item.sequence) for item in self._definitions}

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._last_error = f"Не удалось прочитать назначения клавиш: {exc}"
            return
        if not isinstance(payload, dict) or payload.get("version") != self._FORMAT_VERSION:
            self._last_error = "Файл назначений клавиш имеет неподдерживаемый формат."
            return
        raw_bindings = payload.get("bindings")
        if not isinstance(raw_bindings, dict):
            self._last_error = "В файле назначений клавиш отсутствует раздел bindings."
            return

        loaded = self._default_bindings()
        occupied: dict[str, str] = {}
        for definition in self._definitions:
            candidate = raw_bindings.get(definition.binding_id, definition.sequence)
            if not isinstance(candidate, str):
                candidate = definition.sequence
            normalized = self.normalize_sequence(candidate) or self.normalize_sequence(definition.sequence)
            key = normalized.casefold()
            if key in occupied:
                normalized = self.normalize_sequence(definition.sequence)
                key = normalized.casefold()
            loaded[definition.binding_id] = normalized
            occupied[key] = definition.binding_id
        self._bindings = loaded

    def _write(self, bindings: dict[str, str]) -> str:
        payload = {
            "version": self._FORMAT_VERSION,
            "bindings": bindings,
        }
        temporary = self._storage_path.with_name(f"{self._storage_path.name}.tmp")
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self._storage_path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            self._last_error = f"Не удалось сохранить назначения клавиш: {exc}"
            return self._last_error
        return ""
