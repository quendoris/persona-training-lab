from __future__ import annotations

from types import SimpleNamespace

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
        return [SimpleNamespace(title="dataset_v1", status="Одобрен для обучения", invalid_count=0)]


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


def test_agents_workspace_has_research_roles() -> None:
    vm = _build_vm()
    roles = {role.role_id: role for role in vm.roles()}

    assert "version_navigator" in roles
    assert "researcher" in roles
    assert "dataset_auditor" in roles
    assert "E=+2.00" in roles["researcher"].next_action


def test_agents_workspace_builds_version_tree() -> None:
    vm = _build_vm()
    nodes = vm.version_nodes()

    assert nodes[0].title == "Base model · Qwen local"
    assert any(node.title == "Training · trn_new" for node in nodes)
    assert any(node.title == "Snapshot · mdl_new" for node in nodes)
    assert any("Portrait · portrait new" == node.title for node in nodes)
    assert nodes[-1].subtitle == "E=+2.00 · A=+2.00"


def test_agents_workspace_detail_mentions_current_version() -> None:
    vm = _build_vm()
    detail = vm.selected_detail()

    assert detail.title == "Текущая версия"
    assert "Snapshot new" in detail.body
    assert "Big Five KPI: E=4.00 · A=5.00" in detail.body
    assert "Delta: E=+2.00 · A=+2.00" in detail.body
