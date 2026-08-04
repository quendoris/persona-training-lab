from __future__ import annotations

from PySide6.QtCore import QTimer

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.screen_agents_final import (
    AgentsScreen as _FinalAgentsScreen,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


class AgentsScreen(_FinalAgentsScreen):
    """Final agents workspace with live runtime dependency protection."""

    _RUNTIME_REFRESH_MS = 750

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
        lineage_runtime_safety: LineageRuntimeSafety | None = None,
    ) -> None:
        self._lineage_runtime_safety = lineage_runtime_safety
        self._runtime_blocker_signature: tuple[tuple[str, str, str], ...] = ()
        super().__init__(view_model, key_binding_manager)
        self._runtime_safety_timer = QTimer(self)
        self._runtime_safety_timer.setInterval(self._RUNTIME_REFRESH_MS)
        self._runtime_safety_timer.timeout.connect(
            self._refresh_runtime_safety
        )
        self._runtime_safety_timer.start()
        self._bind_existing_fixed_nodes()
        self._refresh_runtime_safety(force=True)

    def _continue_from_selected(self) -> None:
        parent_id = getattr(self, "_selected_node_id", "")
        fallback_claims = self._runtime_claims_for_node(parent_id)
        super()._continue_from_selected()
        child_id = getattr(self, "_selected_node_id", "")
        safety = self._lineage_runtime_safety
        if safety is None or not child_id:
            return
        if self._state.is_custom_node(parent_id):
            safety.inherit_node(
                child_id,
                parent_id,
                fallback_claims=fallback_claims,
            )
        else:
            safety.bind_node(child_id, fallback_claims)
        self._refresh_runtime_safety(force=True)

    def _delete_local_branch_subtree(self, node_id: str) -> None:
        removed_ids = self._state.custom_subtree_ids(node_id)
        if not removed_ids:
            return
        blockers = self._deletion_blockers(removed_ids)
        if blockers:
            self._show_runtime_blockers(blockers)
            return

        super()._delete_local_branch_subtree(node_id)
        if self._state.is_custom_node(node_id):
            # The confirmation was cancelled; keep dependency links intact.
            return
        safety = self._lineage_runtime_safety
        if safety is not None:
            safety.forget_nodes(removed_ids)
        self._refresh_runtime_safety(force=True)

    def _sync_detail_actions(
        self,
        node_id: str,
        *,
        is_custom: bool,
        is_current: bool,
        is_archived: bool,
    ) -> None:
        super()._sync_detail_actions(
            node_id,
            is_custom=is_custom,
            is_current=is_current,
            is_archived=is_archived,
        )
        if not is_custom:
            return
        subtree_ids = self._state.custom_subtree_ids(node_id)
        blockers = self._deletion_blockers(subtree_ids)
        if not blockers:
            return
        self._delete_action.setEnabled(False)
        self._delete_action.setToolTip(
            "Удаление временно заблокировано активной операцией: "
            + self._lineage_runtime_safety.blocker_text(blockers)
        )

    def _render_detail(self, detail: AgentDetailView) -> None:
        super()._render_detail(detail)
        self._apply_runtime_dependency_text()

    def _refresh_runtime_safety(self, *, force: bool = False) -> None:
        if not self.isVisible() and not force:
            return
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

    def _apply_runtime_dependency_text(self) -> None:
        safety = self._lineage_runtime_safety
        node_id = getattr(self, "_selected_node_id", "")
        if safety is None or not node_id:
            return
        node_ids = (
            self._state.custom_subtree_ids(node_id)
            if self._state.is_custom_node(node_id)
            else (node_id,)
        )
        blockers = self._deletion_blockers(node_ids)
        if blockers:
            base = self._detail_dependency.text().strip()
            runtime_text = (
                "Активная операция удерживает эту точку или её зависимость: "
                + safety.blocker_text(blockers)
                + ". Интерфейс остаётся доступен, но разрушительные действия "
                "временно отключены."
            )
            self._detail_dependency.setText(
                f"{base}\n\n{runtime_text}" if base else runtime_text
            )
            return

        links = safety.links_for_node(node_id)
        if links:
            base = self._detail_dependency.text().strip()
            linked = ", ".join(
                f"{claim.resource_kind}={claim.resource_id}"
                for claim in links
            )
            self._detail_dependency.setText(
                f"{base}\n\nСвязанные реальные ресурсы: {linked}."
            )

    def _show_runtime_blockers(self, blockers) -> None:
        safety = self._lineage_runtime_safety
        if safety is None:
            return
        message = (
            "Удаление не выполнено: точка используется активной операцией. "
            + safety.blocker_text(blockers)
        )
        self._detail_dependency.setText(message)
        self._delete_action.setEnabled(False)
        self._delete_action.setToolTip(message)
        window = self.window()
        status = getattr(window, "_status", None)
        setter = getattr(status, "set_message", None)
        if callable(setter):
            setter(message)

    def _deletion_blockers(self, node_ids):
        safety = self._lineage_runtime_safety
        if safety is None:
            return ()
        return safety.deletion_blockers(node_ids)

    def _bind_existing_fixed_nodes(self) -> None:
        safety = self._lineage_runtime_safety
        if safety is None:
            return
        for node_id in (
            "base",
            "dataset",
            "training",
            "snapshot",
            "portrait",
            "delta",
        ):
            claims = self._runtime_claims_for_node(node_id)
            if claims:
                safety.bind_node(node_id, claims)

    def _runtime_claims_for_node(
        self,
        node_id: str,
    ) -> tuple[ResourceClaim, ...]:
        safety = self._lineage_runtime_safety
        if safety is not None and self._state.is_custom_node(node_id):
            inherited = safety.links_for_node(node_id)
            if inherited:
                return inherited

        claims: list[ResourceClaim] = []
        runs = self._vm._training_runs()  # noqa: SLF001
        versions = self._vm._model_versions()  # noqa: SLF001
        datasets = self._vm._datasets()  # noqa: SLF001
        portraits = self._vm._portraits()  # noqa: SLF001
        latest_run = runs[0] if runs else None
        latest_version = versions[0] if versions else None
        latest_dataset = datasets[0] if datasets else None

        if node_id == "base" and latest_run is not None:
            self._append_claim(
                claims,
                "model_definition",
                getattr(latest_run, "base_model", ""),
            )
        if node_id == "dataset" and latest_dataset is not None:
            self._append_claim(
                claims,
                "dataset",
                getattr(latest_dataset, "dataset_id", "")
                or getattr(latest_dataset, "title", ""),
            )
        if node_id in {"training", "snapshot", "portrait", "delta"}:
            if latest_run is not None:
                self._append_claim(
                    claims,
                    "training_run",
                    getattr(latest_run, "run_id", ""),
                )
                self._append_claim(
                    claims,
                    "dataset",
                    getattr(latest_run, "dataset_version", ""),
                )
                self._append_claim(
                    claims,
                    "profile",
                    getattr(latest_run, "profile", ""),
                )
                self._append_claim(
                    claims,
                    "artifact_path",
                    getattr(latest_run, "artifact_path", ""),
                )
        if node_id in {"snapshot", "portrait", "delta"}:
            if latest_version is not None:
                self._append_claim(
                    claims,
                    "model_version",
                    getattr(latest_version, "version_id", ""),
                )
                self._append_claim(
                    claims,
                    "artifact_path",
                    getattr(latest_version, "artifact_path", ""),
                )
        if node_id in {"portrait", "delta"}:
            limit = 2 if node_id == "delta" else 1
            for portrait in portraits[:limit]:
                self._append_claim(
                    claims,
                    "experiment",
                    getattr(portrait, "experiment_id", ""),
                )
        unique = {claim.key: claim for claim in claims}
        return tuple(sorted(unique.values()))

    @staticmethod
    def _append_claim(
        claims: list[ResourceClaim],
        resource_kind: str,
        resource_id: object,
    ) -> None:
        identifier = str(resource_id or "").strip()
        if identifier:
            claims.append(ResourceClaim(resource_kind, identifier, "read"))
