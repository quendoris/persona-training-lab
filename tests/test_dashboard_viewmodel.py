from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel


def _portrait(title: str, e1: int, e2r: int, a1: int) -> SimpleNamespace:
    subtitle = (
        "PORTRAIT: 3/3 Big Five items · snapshot\n\n"
        f"CASE 1\nTRAIT: Extraversion\nKEY: E1\nREVERSE: 0\nITEM: item\n"
        f"STATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {e1}\n\n"
        f"CASE 2\nTRAIT: Extraversion\nKEY: E2R\nREVERSE: 1\nITEM: item\n"
        f"STATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {e2r}\n\n"
        f"CASE 3\nTRAIT: Agreeableness\nKEY: A1\nREVERSE: 0\nITEM: item\n"
        f"STATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {a1}"
    )
    return SimpleNamespace(
        title=title,
        subtitle=subtitle,
        status="Портрет собран",
    )


class FakeProjectsService:
    def list_projects(self):
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
                progress="100",
                epoch_progress="1 / 1",
                loss="0.01",
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
                quality_summary="artifact сохранён",
            )
        ]


class FakeDatasetsService:
    def list_datasets(self):
        return [
            SimpleNamespace(
                title="dataset_v1",
                status="Одобрен для обучения",
                record_count=10,
                valid_count=10,
                invalid_count=0,
            )
        ]


class FakeExperimentsService:
    def list_experiments(self):
        return [
            _portrait("portrait new", 4, 2, 5),
            _portrait("portrait old", 2, 4, 3),
        ]


def _build_vm() -> DashboardViewModel:
    return DashboardViewModel(
        docs_service=DocsService(),
        projects_service=FakeProjectsService(),
        training_service=FakeTrainingService(),
        model_versions_service=FakeVersionsService(),
        datasets_service=FakeDatasetsService(),
        experiments_service=FakeExperimentsService(),
    )


def test_dashboard_stats_use_semantic_messages_and_live_services() -> None:
    vm = _build_vm()
    stats = vm.stats()

    assert stats[0].label_key == "dashboard.stat.training"
    assert stats[0].value.key == "dashboard.status.completed"
    assert stats[1].value.values["value"] == "01"
    assert stats[2].note.key == "dashboard.note.dataset_summary"
    assert stats[2].note.values == {"approved": 1, "errors": 0}
    assert "E=4.00" in str(stats[3].value.values["value"])
    assert "A=5.00" in str(stats[3].value.values["value"])


def test_dashboard_attention_and_next_step_are_language_neutral() -> None:
    vm = _build_vm()
    attention = {
        item.title_key: item.body
        for item in vm.attention_items()
    }

    delta = attention["dashboard.attention.delta"]
    assert delta.key == "dashboard.raw"
    assert "E=+2.00" in str(delta.values["value"])
    assert "A=+2.00" in str(delta.values["value"])

    step = vm.next_best_step()
    assert step.message.key == "dashboard.step.open_analysis"
    assert step.route.screen == "analysis"
    assert step.route.focus_key == ""


def test_dashboard_lineage_contains_routes_instead_of_parsed_labels() -> None:
    vm = _build_vm()
    lineage = vm.quick_lineage()

    assert lineage[0].label_key == "dashboard.lineage.base_model"
    assert lineage[0].value == "Qwen local"
    assert lineage[0].route.screen == "agents"
    assert lineage[2].value == "trn_new"
    assert lineage[2].route.screen == "training"
    assert lineage[3].value == "mdl_new"
    assert lineage[4].value == "portrait new"
