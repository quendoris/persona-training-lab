from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel


def _portrait(title: str, e1: int, e2r: int, a1: int) -> SimpleNamespace:
    subtitle = (
        "PORTRAIT: 3/3 Big Five items · snapshot\n\n"
        f"CASE 1\nTRAIT: Extraversion\nKEY: E1\nREVERSE: 0\nITEM: item\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {e1}\n\n"
        f"CASE 2\nTRAIT: Extraversion\nKEY: E2R\nREVERSE: 1\nITEM: item\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {e2r}\n\n"
        f"CASE 3\nTRAIT: Agreeableness\nKEY: A1\nREVERSE: 0\nITEM: item\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRESPONSE: SCORE: {a1}"
    )
    return SimpleNamespace(title=title, subtitle=subtitle, status="Портрет собран")


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


def test_dashboard_stats_use_live_services() -> None:
    vm = _build_vm()
    stats = vm.stats()

    assert stats[0][0] == "Обучение"
    assert stats[0][1] == "Завершён"
    assert stats[1][1] == "01"
    assert stats[2][2] == "одобрено 1 · с ошибками 0"
    assert "E=4.00" in stats[3][1]
    assert "A=5.00" in stats[3][1]


def test_dashboard_attention_shows_delta() -> None:
    vm = _build_vm()
    attention = dict(vm.attention_items())

    assert "Delta" in attention
    assert "E=+2.00" in attention["Delta"]
    assert "A=+2.00" in attention["Delta"]
    assert vm.next_best_step() == "Откройте «Анализ» и смотрите delta latest - previous."


def test_dashboard_lineage_is_live() -> None:
    vm = _build_vm()
    lineage = vm.quick_lineage()

    assert "Base model · Qwen local" in lineage
    assert "Training · trn_new" in lineage
    assert "Snapshot · mdl_new" in lineage
    assert "Portrait · portrait new" in lineage
