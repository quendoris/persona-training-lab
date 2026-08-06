from __future__ import annotations

from persona_training_lab.ui.agents.refresh_worker import LineageRefreshFailure
from persona_training_lab.ui.agents.screen_background_fast import (
    AgentsScreen as _BackgroundAgentsScreen,
)


class AgentsScreen(_BackgroundAgentsScreen):
    """Report refresh failures without discarding the last good projection."""

    def _on_projection_failed(self, failure: LineageRefreshFailure) -> None:
        reporter = getattr(self._vm, "lineage_error_reporter", None)
        correlation = ""
        if reporter is not None:
            correlation = reporter.report_message(
                "Lineage refresh failed: "
                f"{failure.error_type}: {failure.message}",
                component="ui.agents.lineage_refresh",
                level="ERROR",
                entity_kind="lineage_refresh",
                entity_id=str(failure.generation),
                context={
                    "generation": failure.generation,
                    "error_type": failure.error_type,
                    "traceback": failure.traceback_text,
                    "last_good_available": (
                        self._lineage_refresh_coordinator is not None
                        and self._lineage_refresh_coordinator.last_good is not None
                    ),
                },
            )

        super()._on_projection_failed(failure)
        if not correlation:
            return
        window = self.window()
        status = getattr(window, "_status", None)
        setter = getattr(status, "set_message", None)
        if callable(setter):
            setter(
                "Lineage refresh не обновлён; сохранён последний "
                f"согласованный снимок. Код события: {correlation}."
            )
