from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.application.experiments.service import (
    experiment_result,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)
from persona_training_lab.ui.agents.screen_contextual import (
    AgentsScreen as ContextualAgentsScreen,
)
from persona_training_lab.ui.shell.main_window_context import (
    MainWindow as ContextMainWindow,
)
from persona_training_lab.ui.viewmodels.analysis_lineage import AnalysisViewModel
from persona_training_lab.ui.viewmodels.evaluation import EvaluationText
from persona_training_lab.ui.viewmodels.tests_lineage import TestsViewModel


class _Experiments:
    def __init__(self, items=()) -> None:
        self.items = list(items)
        self.requested_version: str | None = None

    def list_experiments(self):
        return list(self.items)

    def run_personality_portrait_test_pack(self, model_version_id=None):
        self.requested_version = model_version_id
        return experiment_result(
            True,
            "готово",
            message_code="portrait_completed",
            model_version_id=model_version_id or "",
            passed=1,
            total=1,
        )


def _portrait(
    experiment_id: str,
    title: str,
    version_id: str,
    score: int,
):
    return SimpleNamespace(
        experiment_id=experiment_id,
        title=title,
        status="Портрет собран",
        status_code=EvaluationRunStatus.COMPLETED,
        subtitle=(
            "PORTRAIT: 1/1 Big Five items · "
            f"model_version={version_id} · artifact=/models/{version_id} · "
            "battery=v1 · scoring=s1\n\n"
            "CASE 1\nTRAIT: Openness\nKEY: O1\nREVERSE: 0\n"
            "VALID_SCORE: 1\nSTATUS: Модель отвечает\n"
            f"RESPONSE: SCORE: {score}"
        ),
    )


def test_tests_viewmodel_runs_exact_selected_model_version() -> None:
    service = _Experiments()
    vm = TestsViewModel(experiments_service=service)

    vm.set_lineage_context(
        {
            "node_id": "version:mdl_old",
            "model_version_id": "mdl_old",
            "artifact_path": "/models/mdl_old",
        }
    )
    result = vm.run_tests_sync()

    assert result.ok is True
    assert result.message == "готово"
    assert result.message_code == "portrait_completed"
    assert service.requested_version == "mdl_old"
    assert ("Версия", "mdl_old") in vm.setup_rows
    assert ("Веса", "/models/mdl_old") in vm.setup_rows


def test_tests_viewmodel_never_displays_another_versions_portrait() -> None:
    service = _Experiments(
        [_portrait("evr_new", "New", "mdl_new", 5)]
    )
    vm = TestsViewModel(experiments_service=service)

    vm.set_lineage_context(
        {
            "node_id": "version:mdl_old",
            "model_version_id": "mdl_old",
            "artifact_path": "/models/mdl_old",
        }
    )

    assert vm.title == "Тесты · mdl_old"
    assert vm.header_subtitle_model() == EvaluationText(
        "tests.header.subtitle.target_empty"
    )
    assert vm.metrics[0].value == "0"
    assert vm.case_title_model(vm.problematic_cases[0]) == EvaluationText(
        "tests.case.target_empty.title"
    )


def test_analysis_uses_exact_selected_and_current_portraits() -> None:
    service = _Experiments(
        [
            _portrait("evr_unrelated", "Unrelated", "mdl_other", 1),
            _portrait("evr_selected", "Selected portrait", "mdl_old", 2),
            _portrait(
                "evr_current",
                "Current portrait",
                "mdl_current",
                5,
            ),
        ]
    )
    vm = AnalysisViewModel(experiments_service=service)

    vm.set_lineage_context(
        {
            "selected": {
                "node_id": "version:mdl_old",
                "model_version_id": "mdl_old",
            },
            "current": {
                "node_id": "snapshot",
                "model_version_id": "mdl_current",
            },
        }
    )

    assert vm.title == "Анализ · mdl_old ↔ mdl_current"
    assert vm.left.subtitle == "Selected portrait"
    assert vm.right.subtitle == "Current portrait"
    assert vm.metrics[1].delta == "O=+3.00"


def test_analysis_does_not_substitute_missing_portrait() -> None:
    service = _Experiments(
        [_portrait("evr_current", "Current", "mdl_current", 4)]
    )
    vm = AnalysisViewModel(experiments_service=service)

    vm.set_lineage_context(
        {
            "selected": {"model_version_id": "mdl_missing"},
            "current": {"model_version_id": "mdl_current"},
        }
    )

    subtitle = vm.header_subtitle_model()
    assert isinstance(subtitle, EvaluationText)
    assert subtitle.key == "analysis.header.subtitle.pair_missing"
    reason = subtitle.values["reason"]
    assert isinstance(reason, EvaluationText)
    assert reason.key == "analysis.pair.reason.portrait_missing"
    assert reason.values["missing"] == "mdl_missing"
    assert vm.metrics[1].delta == "—"


def test_custom_branch_context_is_derived_from_inherited_resources() -> None:
    node = SimpleNamespace(
        title="Experiment branch",
        status="локальная",
    )
    screen = SimpleNamespace(
        _node_context=lambda _node_id: {},
        _node_by_id=lambda _node_id: node,
        _render_text=lambda value: value,
        _runtime_claims_for_node=lambda _node_id: (
            ResourceClaim("model_version", "mdl_parent", "read"),
            ResourceClaim("artifact_path", "/models/mdl_parent", "read"),
            ResourceClaim("training_run", "trn_parent", "read"),
        ),
    )

    context = ContextualAgentsScreen._context_for_node(
        screen,
        "branch_001",
    )

    assert context["node_id"] == "branch_001"
    assert context["model_version_id"] == "mdl_parent"
    assert context["artifact_path"] == "/models/mdl_parent"
    assert context["training_run_id"] == "trn_parent"


def test_main_window_delivers_context_before_navigation() -> None:
    calls: list[tuple[str, object]] = []
    view_model = SimpleNamespace(
        set_lineage_context=lambda payload: calls.append(
            ("context", payload)
        )
    )
    target = SimpleNamespace(
        _vm=view_model,
        _refresh_all=lambda: calls.append(("refresh", None)),
    )
    window = SimpleNamespace(
        _workspace=SimpleNamespace(
            workspace=lambda key: target if key == "tests" else None
        ),
        _go_to_screen=lambda key: calls.append(("navigate", key)),
    )
    payload = {"model_version_id": "mdl_old"}

    ContextMainWindow._go_to_screen_with_context(
        window,
        "tests",
        payload,
    )

    assert calls == [
        ("context", payload),
        ("refresh", None),
        ("navigate", "tests"),
    ]
