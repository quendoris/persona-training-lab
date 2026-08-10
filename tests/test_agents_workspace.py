from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel


def _portrait(title: str, e1: int, e2r: int, a1: int) -> SimpleNamespace:
    subtitle = (
        "PORTRAIT: 3/3 Big Five items · snapshot\n\n"
        f"CASE 1\nTRAIT: Extraversion\nKEY: E1\nREVERSE: 0\nITEM: item\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {e1}\n\n"
        f"CASE 2\nTRAIT: Extraversion\nKEY: E2R\nREVERSE: 1\nITEM: item\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {e2r}\n\n"
        f"CASE 3\nTRAIT: Agreeableness\nKEY: A1\nREVERSE: 0\nITEM: item\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {a1}"
    )
    return SimpleNamespace(title=title, subtitle=subtitle, status="Портрет собран")


class FakeAgentsService:
    def list_agents(self):
        return []


class FakeTrainingService:
    def list_training_runs(self):
        return [
            SimpleNamespace(
                run_id="trn_new",
                title="Training new",
                status="Завершён",
                base_model="Qwen local",
                dataset_version="dataset_v1",
                artifact_path="artifacts/full_finetune/trn_new/model",
                epoch_progress="1 / 1",
                loss="0.01",
            )
        ]


class FakeVersionsService:
    def list_model_versions(self):
        return [
            SimpleNamespace(
                version_id="mdl_new",
                title="Snapshot new",
                status="Готова",
                artifact_path="artifacts/full_finetune/trn_new/model",
            )
        ]


class FakeDatasetsService:
    def list_datasets(self):
        return [
            SimpleNamespace(
                title="dataset_v1",
                status="Одобрен для обучения",
                invalid_count=0,
                record_count=10,
                valid_count=10,
            )
        ]


class FakeExperimentsService:
    def list_experiments(self):
        return [_portrait("portrait new", 4, 2, 5), _portrait("portrait old", 2, 4, 3)]


def _build_vm() -> AgentsViewModel:
    return AgentsViewModel(
        agents_service=FakeAgentsService(),
        training_service=FakeTrainingService(),
        model_versions_service=FakeVersionsService(),
        datasets_service=FakeDatasetsService(),
        experiments_service=FakeExperimentsService(),
    )


def _message(value: object, key: str) -> UserMessage:
    assert isinstance(value, UserMessage)
    assert value.key == key
    return value


def test_agents_workspace_has_research_roles() -> None:
    vm = _build_vm()
    roles = {role.role_id: role for role in vm.roles()}

    assert "version_navigator" in roles
    assert "researcher" in roles
    assert "dataset_auditor" in roles
    next_action = _message(
        roles["researcher"].next_action,
        "agents.legacy.role.researcher.next",
    )
    assert next_action.values["delta"] == "E=+2.00 · A=+2.00"


def test_agents_workspace_builds_version_tree() -> None:
    vm = _build_vm()
    nodes = vm.version_nodes()

    assert nodes[0].node_id == "base"
    base_title = _message(nodes[0].title, "agents.node.title.base_model")
    assert base_title.values["label"] == "Qwen local"
    assert nodes[0].tone == "good"

    training = next(node for node in nodes if node.node_id == "training")
    training_title = _message(
        training.title,
        "agents.node.title.training_run",
    )
    assert training_title.values["label"] == "trn_new"

    snapshot = next(node for node in nodes if node.node_id == "snapshot")
    snapshot_title = _message(
        snapshot.title,
        "agents.node.title.model_version",
    )
    assert snapshot_title.values["label"] == "mdl_new"

    portrait = next(node for node in nodes if node.node_id == "portrait")
    portrait_title = _message(
        portrait.title,
        "agents.node.title.evaluation_run",
    )
    assert portrait_title.values["label"] == "portrait new"

    assert nodes[-1].node_id == "delta"
    delta_subtitle = _message(
        nodes[-1].subtitle,
        "agents.legacy.node.delta.ready",
    )
    assert delta_subtitle.values["delta"] == "E=+2.00 · A=+2.00"
    assert nodes[-1].tone == "good"


def test_agents_workspace_detail_mentions_current_version() -> None:
    vm = _build_vm()
    detail = vm.selected_detail()

    _message(detail.title, "agents.node.kind.model_version")
    body = _message(detail.body, "agents.legacy.detail.version.body")
    assert body.values["title"] == "Snapshot new"
    assert body.values["scores"] == "E=4.00 · A=5.00"
    assert body.values["delta"] == "E=+2.00 · A=+2.00"
    action_keys = {
        _message(action, action.key).key
        for action in detail.actions
        if isinstance(action, UserMessage)
    }
    assert {
        "agents.legacy.detail.version.action.current",
        "agents.legacy.detail.version.action.failed",
        "agents.legacy.detail.version.action.rollback",
    } <= action_keys


def test_agents_workspace_node_details_are_specific() -> None:
    vm = _build_vm()

    dataset = vm.node_detail("dataset")
    training = vm.node_detail("training")
    portrait = vm.node_detail("portrait")
    delta = vm.node_detail("delta")

    _message(dataset.title, "agents.node.kind.dataset")
    dataset_body = _message(
        dataset.body,
        "agents.legacy.detail.dataset.body",
    )
    assert dataset_body.values["title"] == "dataset_v1"
    dataset_action_keys = {
        action.key
        for action in dataset.actions
        if isinstance(action, UserMessage)
    }
    assert "agents.legacy.detail.dataset.action.training" in dataset_action_keys

    training_body = _message(
        training.body,
        "agents.legacy.detail.training.body",
    )
    assert training_body.values["run"] == "trn_new"
    assert training_body.values["artifact"] == (
        "artifacts/full_finetune/trn_new/model"
    )

    portrait_body = _message(
        portrait.body,
        "agents.legacy.detail.portrait.body",
    )
    assert portrait_body.values["scores"] == "E=4.00 · A=5.00"

    delta_body = _message(delta.body, "agents.legacy.detail.delta.body")
    assert delta_body.values["latest"] == "portrait new"
    assert delta_body.values["previous"] == "portrait old"
