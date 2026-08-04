from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyBindingDefinition:
    binding_id: str
    sequence: str
    title: str
    description: str
    auto_repeat: bool = False
    editable: bool = True
    category: str = "История и ветки"


@dataclass(frozen=True, slots=True)
class MouseBindingDefinition:
    binding_id: str
    button: str
    modifier: str
    trigger: str
    target: str
    title: str
    description: str
    category: str = "Мышь и canvas"


MOUSE_BUTTON_LABELS: dict[str, str] = {
    "left": "Левая кнопка",
    "right": "Правая кнопка",
    "middle": "Средняя кнопка",
    "back": "Боковая назад",
    "forward": "Боковая вперёд",
    "wheel": "Колесо мыши",
}

MOUSE_MODIFIER_LABELS: dict[str, str] = {
    "none": "Без модификатора",
    "shift": "Shift",
    "control": "Ctrl",
    "alt": "Alt",
    "meta": "Meta",
}


_GRAPH_BINDING_IDS = frozenset(
    {"delete_branch", "history_toggle", "undo_only"}
)


AGENT_GRAPH_KEY_BINDINGS: tuple[KeyBindingDefinition, ...] = (
    KeyBindingDefinition(
        binding_id="delete_branch",
        sequence="Del",
        title="Удалить выбранную ветку",
        description="Открывает подтверждение удаления выбранной локальной ветки и её поддерева.",
    ),
    KeyBindingDefinition(
        binding_id="history_toggle",
        sequence="Ctrl+Z",
        title="Отменить или вернуть последнее изменение",
        description="Первое нажатие отменяет последний шаг, второе возвращает его; повторные нажатия переключают состояние до и после.",
    ),
    KeyBindingDefinition(
        binding_id="undo_only",
        sequence="Ctrl+Shift+Z",
        title="Последовательно уходить назад по истории",
        description="Всегда отменяет ещё один шаг; при удержании повторяет отмену.",
        auto_repeat=True,
    ),
    KeyBindingDefinition(
        binding_id="nav_dashboard",
        sequence="Alt+H",
        title="Открыть панель управления",
        description="Переключает приложение на главную панель из любой вкладки.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_profiles",
        sequence="Alt+P",
        title="Открыть профили",
        description="Переключает приложение на вкладку профилей.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_agents",
        sequence="Alt+A",
        title="Открыть агентов",
        description="Переключает приложение на lineage-дерево агентов и версий.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_datasets",
        sequence="Alt+D",
        title="Открыть датасеты",
        description="Переключает приложение на вкладку датасетов.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_training",
        sequence="Alt+T",
        title="Открыть обучение",
        description="Переключает приложение на вкладку обучения.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_snapshots",
        sequence="Alt+S",
        title="Открыть снимки",
        description="Переключает приложение на реестр снимков и весов.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_tests",
        sequence="Alt+E",
        title="Открыть тесты",
        description="Переключает приложение на вкладку тестирования и портретов.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_analysis",
        sequence="Alt+L",
        title="Открыть анализ",
        description="Переключает приложение на вкладку анализа результатов.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_style",
        sequence="Alt+Y",
        title="Открыть оформление",
        description="Переключает приложение на вкладку тем, акцента и масштаба.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_docs",
        sequence="Alt+O",
        title="Открыть документацию",
        description="Переключает приложение на вкладку документации.",
        category="Навигация по вкладкам",
    ),
    KeyBindingDefinition(
        binding_id="nav_keybindings",
        sequence="Alt+K",
        title="Открыть назначения клавиш",
        description="Переключает приложение на редактор клавиатуры и мыши.",
        category="Навигация по вкладкам",
    ),
)


AGENT_GRAPH_MOUSE_BINDINGS: tuple[MouseBindingDefinition, ...] = (
    MouseBindingDefinition(
        binding_id="open_node_menu",
        button="left",
        modifier="none",
        trigger="click",
        target="node",
        title="Открыть действия узла",
        description="Выбирает точку и открывает встроенное меню действий прямо на canvas.",
    ),
    MouseBindingDefinition(
        binding_id="close_node_menu",
        button="left",
        modifier="none",
        trigger="click",
        target="canvas",
        title="Закрыть меню узла",
        description="Скрывает открытое меню кликом по пустому месту.",
    ),
    MouseBindingDefinition(
        binding_id="pan_canvas_primary",
        button="left",
        modifier="none",
        trigger="drag",
        target="canvas",
        title="Перемещать пространство — основной жест",
        description="Панорамирует рабочую область графа по пустому canvas.",
    ),
    MouseBindingDefinition(
        binding_id="pan_canvas_secondary",
        button="right",
        modifier="none",
        trigger="drag",
        target="canvas",
        title="Перемещать пространство — дополнительный жест",
        description="Второй независимый способ панорамирования рабочей области.",
    ),
    MouseBindingDefinition(
        binding_id="move_node",
        button="right",
        modifier="none",
        trigger="drag",
        target="node",
        title="Перемещать одну точку",
        description="Меняет ручное положение только выбранного узла.",
    ),
    MouseBindingDefinition(
        binding_id="move_subtree",
        button="right",
        modifier="shift",
        trigger="drag",
        target="node",
        title="Перемещать поддерево",
        description="Перемещает выбранную точку вместе с дочерними узлами; режим меняется динамически при нажатии модификатора.",
    ),
    MouseBindingDefinition(
        binding_id="zoom_canvas",
        button="wheel",
        modifier="none",
        trigger="wheel",
        target="canvas",
        title="Масштабировать граф",
        description="Изменяет масштаб относительно позиции курсора.",
    ),
)


def agent_graph_key_bindings_by_id() -> dict[str, KeyBindingDefinition]:
    return {
        binding.binding_id: binding
        for binding in AGENT_GRAPH_KEY_BINDINGS
        if binding.binding_id in _GRAPH_BINDING_IDS
    }


def agent_graph_mouse_bindings_by_id() -> dict[str, MouseBindingDefinition]:
    return {binding.binding_id: binding for binding in AGENT_GRAPH_MOUSE_BINDINGS}
