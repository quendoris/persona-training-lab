from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyBindingDefinition:
    binding_id: str
    sequence: str
    title: str
    description: str
    auto_repeat: bool = False


AGENT_GRAPH_KEY_BINDINGS: tuple[KeyBindingDefinition, ...] = (
    KeyBindingDefinition(
        binding_id="delete_branch",
        sequence="Del",
        title="Удалить выбранную ветку",
        description="Открывает подтверждение удаления выбранной локальной ветки и её поддерева.",
    ),
    KeyBindingDefinition(
        binding_id="undo_once",
        sequence="Ctrl+Z",
        title="Отменить одно действие",
        description="Откатывает последнее изменение lineage. Каждое новое нажатие делает ещё один шаг назад.",
    ),
    KeyBindingDefinition(
        binding_id="undo_many",
        sequence="Ctrl+Shift+Z",
        title="Быстрая последовательная отмена",
        description="Откатывает один шаг; при удержании повторяет отмену по системной частоте клавиатуры.",
        auto_repeat=True,
    ),
)


def agent_graph_key_bindings_by_id() -> dict[str, KeyBindingDefinition]:
    return {binding.binding_id: binding for binding in AGENT_GRAPH_KEY_BINDINGS}
