from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.ui.agents.atomic_lineage_public import (
    build_empty_lineage,
)
from persona_training_lab.ui.agents.lineage import build_version_lineage
from persona_training_lab.ui.agents.projection_runtime import (
    LineageRefreshIncidentReporter,
    ProjectionSafetyBinding,
)
from persona_training_lab.ui.agents.projection_updates import (
    ProjectionUpdateKind,
    ProjectionUpdatePlanner,
)
from persona_training_lab.ui.agents.refresh_coordinator import (
    LineageRefreshCoordinator,
)
from persona_training_lab.ui.agents.refresh_worker import (
    LineageRefreshFailure,
    LineageRefreshResult,
)
from persona_training_lab.ui.agents.screen_runtime_safe import (
    AgentsScreen as _RuntimeSafeAgentsScreen,
)
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager


class AgentsScreen(_RuntimeSafeAgentsScreen):
    """Runtime-safe Agents UI fed by a worker-owned atomic projection."""

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
        lineage_runtime_safety: LineageRuntimeSafety | None = None,
        lineage_refresh_coordinator: LineageRefreshCoordinator | None = None,
    ) -> None:
        coordinator = lineage_refresh_coordinator
        owns_coordinator = False
        if coordinator is None:
            loader_factory = getattr(
                view_model,
                "lineage_loader_factory",
                None,
            )
            if loader_factory is not None:
                coordinator = LineageRefreshCoordinator(loader_factory)
                owns_coordinator = True
        self._lineage_refresh_coordinator = coordinator
        self._owns_lineage_refresh_coordinator = owns_coordinator
        self._projection_safety_binding = ProjectionSafetyBinding(
            lineage_runtime_safety
        )
        self._refresh_incident_reporter = LineageRefreshIncidentReporter(
            getattr(view_model, "lineage_error_reporter", None)
        )
        self._projection_update_planner = ProjectionUpdatePlanner()
        try:
            super().__init__(
                view_model,
                key_binding_manager,
                lineage_runtime_safety,
            )
        except Exception:
            if owns_coordinator and coordinator is not None:
                coordinator.shutdown()
            raise

        if coordinator is None:
            return
        if owns_coordinator:
            coordinator.setParent(self)
        self._runtime_safety_timer.stop()
        coordinator.projection_ready.connect(self._on_projection_ready)
        coordinator.refresh_failed.connect(self._on_projection_failed)
        last_good = coordinator.last_good
        if last_good is not None:
            self._on_projection_ready(last_good)

    def _build_nodes(self):
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            return super()._build_nodes()
        result = coordinator.last_good
        projection = (
            result.projection if result is not None else build_empty_lineage()
        )
        self._real_projection = projection
        self._real_projection_signature = projection.signature
        return self._state.apply(build_version_lineage(projection.nodes))

    def _bind_projection_resources(self) -> None:
        projection = self._real_projection
        if projection is None:
            return
        coordinator = self._lineage_refresh_coordinator
        snapshot_proven = (
            coordinator is None or coordinator.last_good is not None
        )
        self._projection_safety_binding.reconcile(
            projection.resources,
            snapshot_proven=snapshot_proven,
        )

    def _roles(self) -> QWidget:
        if self._lineage_refresh_coordinator is None:
            return super()._roles()
        content = QWidget()
        content.setProperty("transparentBg", True)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        card = PanelCard(
            "Рабочие роли",
            "Подсказки рассчитаны из того же атомарного lineage snapshot.",
        )
        self._projection_roles_layout = QVBoxLayout()
        self._projection_roles_layout.setSpacing(8)
        card._layout.addLayout(self._projection_roles_layout)
        layout.addWidget(card)
        layout.addStretch(1)
        self._roles_content = content
        self._refresh_projection_roles()
        return self._bounded_column_scroll(
            content,
            object_name="AgentsRolesScroll",
            minimum_width=self._ROLES_MIN_WIDTH,
            maximum_width=self._ROLES_MAX_WIDTH,
        )

    def _refresh_projection_roles(self) -> None:
        layout = getattr(self, "_projection_roles_layout", None)
        if layout is None:
            return
        self._clear_layout(layout)
        for title, mission, next_action, status in self._projection_roles():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            title_label = QLabel(title)
            title_label.setObjectName("CardTitle")
            row_layout.addWidget(title_label)
            row_layout.addWidget(make_muted_label(mission))
            row_layout.addWidget(make_muted_label(next_action))
            row_layout.addWidget(make_status_label(status, "pending"))
            layout.addWidget(row)

    def _projection_roles(
        self,
    ) -> tuple[tuple[str, str, str, str], ...]:
        projection = self._real_projection
        if projection is None:
            return ()
        contexts = projection.entity_context
        real_contexts = tuple(
            context
            for context in contexts.values()
            if not self._is_placeholder_context(context)
        )
        dataset_count = sum(
            context.get("node_kind") == "dataset"
            for context in real_contexts
        )
        evaluation_count = sum(
            context.get("node_kind") == "evaluation_run"
            for context in real_contexts
        )
        bad_count = sum(node.tone == "bad" for node in projection.nodes)
        pending_count = sum(
            node.tone == "pending"
            and not self._is_placeholder_context(
                contexts.get(node.node_id, {})
            )
            for node in projection.nodes
        )
        unresolved_count = sum(
            "unresolved:" in node.subtitle
            for node in projection.nodes
        )
        snapshot_context = contexts.get("snapshot", {})
        current_version = snapshot_context.get("model_version_id", "")
        delta_context = contexts.get("delta", {})
        delta_ready = bool(
            delta_context.get("left_experiment_id")
            and delta_context.get("right_experiment_id")
        )
        next_action = self._projection_next_action(contexts, delta_ready)
        return (
            (
                "Версионный навигатор",
                "Следит за причинной цепочкой model lineage.",
                next_action,
                "главный",
            ),
            (
                "Исследователь",
                "Сверяет реальные evaluation runs и delta.",
                f"Портретов: {evaluation_count}; delta: "
                + ("готова" if delta_ready else "нужен второй запуск"),
                "анализ",
            ),
            (
                "Аудитор датасета",
                "Проверяет состояние данных до продолжения обучения.",
                f"Датасетов: {dataset_count}; проблемных узлов: {bad_count}.",
                "проверка",
            ),
            (
                "Протоколист",
                "Не позволяет скрыть разорванные зависимости.",
                f"Unresolved связей: {unresolved_count}; current: "
                f"{current_version or '—'}.",
                "протокол",
            ),
            (
                "Разметчик",
                "Готовит corrective data по неустойчивым результатам.",
                f"Ожидающих или partial узлов: {pending_count}.",
                "позже",
            ),
        )

    @staticmethod
    def _is_placeholder_context(context: Mapping[str, str]) -> bool:
        return context.get("node_kind", "").endswith("_placeholder")

    @classmethod
    def _projection_next_action(
        cls,
        contexts: Mapping[str, Mapping[str, str]],
        delta_ready: bool,
    ) -> str:
        for node_id, action in (
            ("dataset", "Добавьте и проверьте датасет."),
            ("training", "Создайте и завершите training run."),
            ("snapshot", "Зарегистрируйте model version из artifact."),
            ("portrait", "Соберите портрет текущей model version."),
        ):
            if cls._is_placeholder_context(contexts.get(node_id, {})):
                return action
        if not delta_ready:
            return "Соберите второй сопоставимый portrait для delta."
        return "Откройте анализ и проверьте следующую ветку."

    def _refresh_runtime_safety(self, *, force: bool = False) -> None:
        if self._lineage_refresh_coordinator is None:
            super()._refresh_runtime_safety(force=force)
            return
        self._refresh_runtime_blockers(force=force)

    def _refresh_runtime_blockers(self, *, force: bool = False) -> None:
        node_id = getattr(self, "_selected_node_id", "")
        node = self._node_by_id(node_id) if node_id else None
        if node is None:
            return
        node_ids = (
            self._state.custom_subtree_ids(node_id)
            if self._state.is_custom_node(node_id)
            else (node_id,)
        )
        blockers = self._deletion_blockers(node_ids)
        signature = tuple(
            sorted(
                (
                    blocker.operation.operation_id,
                    blocker.claim.resource_kind,
                    blocker.claim.resource_id,
                )
                for blocker in blockers
            )
        )
        if not force and signature == self._runtime_blocker_signature:
            return
        self._runtime_blocker_signature = signature
        self._select_node(node_id)

    def request_projection_refresh(self, *, force: bool = True) -> None:
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None:
            coordinator.request_refresh(force=force)

    def shutdown_background_work(self, timeout_ms: int = 6_500) -> bool:
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            return True
        return coordinator.shutdown(timeout_ms)

    def showEvent(self, event: QShowEvent) -> None:  # type: ignore[override]
        super().showEvent(event)
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None:
            coordinator.set_active(True)

    def hideEvent(self, event: QHideEvent) -> None:  # type: ignore[override]
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None:
            coordinator.set_active(False)
        super().hideEvent(event)

    def _on_projection_ready(self, result: LineageRefreshResult) -> None:
        plan = self._projection_update_planner.plan(result.revisions)
        if plan is ProjectionUpdateKind.NOOP:
            self._refresh_runtime_blockers(force=False)
            return
        if plan is ProjectionUpdateKind.FULL:
            self._apply_projection(result.projection)
        elif not self._apply_projection_content(result):
            self._apply_projection(result.projection)

        self._projection_update_planner.commit(result.revisions)
        self._refresh_projection_roles()
        self._refresh_runtime_blockers(force=True)

    def _apply_projection_content(
        self,
        result: LineageRefreshResult,
    ) -> bool:
        projection = result.projection
        next_nodes = self._state.apply(
            build_version_lineage(projection.nodes)
        )
        updater = getattr(self._graph, "update_node_content", None)
        if not callable(updater) or not updater(next_nodes):
            return False

        selected = getattr(self, "_selected_node_id", "")
        self._real_projection = projection
        self._real_projection_signature = projection.signature
        self._lineage_nodes = next_nodes
        self._bind_projection_resources()
        if selected and self._node_by_id(selected) is not None:
            self._select_node(selected)
        return True

    def _on_projection_failed(self, failure: LineageRefreshFailure) -> None:
        coordinator = self._lineage_refresh_coordinator
        last_good_available = (
            coordinator is not None and coordinator.last_good is not None
        )
        correlation = self._refresh_incident_reporter.report(
            failure,
            last_good_available=last_good_available,
        )
        window = self.window()
        status = getattr(window, "_status", None)
        setter = getattr(status, "set_message", None)
        if not callable(setter):
            return
        if correlation:
            setter(
                "Lineage refresh не обновлён; сохранён последний "
                f"согласованный снимок. Код события: {correlation}."
            )
            return
        setter(
            "Lineage refresh не обновлён; сохранён последний "
            f"согласованный снимок ({failure.error_type})."
        )
