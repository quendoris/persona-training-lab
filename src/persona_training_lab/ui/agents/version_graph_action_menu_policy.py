from __future__ import annotations

from collections.abc import Callable

from persona_training_lab.ui.agents.version_graph_layout_history import (
    VersionGraphCanvas as LayoutHistoryVersionGraphCanvas,
)
from persona_training_lab.ui.i18n.text import text as localized_text


class VersionGraphCanvas(LayoutHistoryVersionGraphCanvas):
    """Own graph action-menu contents and history-action presentation."""

    def __init__(self, nodes) -> None:
        self._history_action_text: str | None = None
        self._action_text_resolver: Callable[..., str] | None = None
        self._archive_state_resolver: Callable[[str], bool] | None = None
        super().__init__(nodes)

    def set_action_text_resolver(
        self,
        resolver: Callable[..., str],
    ) -> None:
        self._action_text_resolver = resolver
        self.update()

    def set_archive_state_resolver(
        self,
        resolver: Callable[[str], bool],
    ) -> None:
        self._archive_state_resolver = resolver
        self.update()

    def close_node_menu(self) -> None:
        self._menu_node_id = None
        self.update()

    def set_history_action_text(self, text: str | None) -> None:
        self._history_action_text = text.strip() if text else None
        self.update()

    def set_undo_action_label(self, label: str | None) -> None:
        # Compatibility with older screen code while the history UI migrates.
        self.set_history_action_text(
            self._menu_text("agents.history.undo", action=label)
            if label
            else None
        )

    def _menu_actions(self) -> tuple[tuple[str, str], ...]:
        actions: list[tuple[str, str]] = [
            ("make_current", self._menu_text("agents.menu.make_current")),
            ("mark_good", self._menu_text("agents.menu.mark_good")),
            ("mark_pending", self._menu_text("agents.menu.mark_pending")),
            ("mark_bad", self._menu_text("agents.menu.mark_bad")),
            ("continue", self._menu_text("agents.menu.continue")),
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
            archived = (
                self._archive_state_resolver(node.node_id)
                if self._archive_state_resolver is not None
                else False
            )
            actions.extend(
                (
                    ("rename", self._menu_text("agents.menu.rename")),
                    (
                        "archive_toggle",
                        self._menu_text(
                            "agents.menu.unarchive"
                            if archived
                            else "agents.menu.archive"
                        ),
                    ),
                    (
                        "delete_subtree",
                        self._menu_text("agents.menu.delete_subtree"),
                    ),
                )
            )
        actions.extend(
            (
                ("center", self._menu_text("agents.menu.center")),
                (
                    "reset_node",
                    self._menu_text("agents.menu.reset_node"),
                ),
                (
                    "reset_subtree",
                    self._menu_text("agents.menu.reset_subtree"),
                ),
            )
        )
        return tuple(actions)

    def _menu_text(self, key: str, **values: object) -> str:
        resolver = self._action_text_resolver
        if resolver is not None:
            return resolver(key, **values)
        return localized_text(None, key, **values)
