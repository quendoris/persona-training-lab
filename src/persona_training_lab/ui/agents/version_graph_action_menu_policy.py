from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_layout_history import (
    VersionGraphCanvas as LayoutHistoryVersionGraphCanvas,
)


class VersionGraphCanvas(LayoutHistoryVersionGraphCanvas):
    """Own graph action-menu contents and history-action presentation."""

    def __init__(self, nodes) -> None:
        self._history_action_text: str | None = None
        super().__init__(nodes)

    def close_node_menu(self) -> None:
        self._menu_node_id = None
        self.update()

    def set_history_action_text(self, text: str | None) -> None:
        self._history_action_text = text.strip() if text else None
        self.update()

    def set_undo_action_label(self, label: str | None) -> None:
        # Compatibility with older screen code while the history UI migrates.
        self.set_history_action_text(f"Отменить: {label}" if label else None)

    def _menu_actions(self) -> tuple[tuple[str, str], ...]:
        actions: list[tuple[str, str]] = [
            ("make_current", "Сделать актуальной"),
            ("mark_good", "Пометить удачной"),
            ("mark_pending", "Пометить спорной"),
            ("mark_bad", "Пометить неудачной"),
            ("continue", "Продолжить от этой точки"),
        ]
        if self._history_action_text:
            actions.append(("history_toggle", self._history_action_text))
        node = next(
            (
                item
                for item in self._nodes
                if item.node_id == self._menu_node_id
            ),
            None,
        )
        if node is not None and node.node_id.startswith("branch_"):
            actions.extend(
                (
                    ("rename", "Переименовать ветку"),
                    (
                        "archive_toggle",
                        "Вернуть из архива"
                        if getattr(node, "status", "") == "архивная"
                        else "Архивировать ветку",
                    ),
                    ("delete_subtree", "Удалить ветку и поддерево"),
                )
            )
        actions.extend(
            (
                ("center", "Центрировать на точке"),
                ("reset_node", "Сбросить смещение точки"),
                ("reset_subtree", "Сбросить смещение поддерева"),
            )
        )
        return tuple(actions)
