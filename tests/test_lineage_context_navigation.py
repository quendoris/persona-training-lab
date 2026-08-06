from __future__ import annotations

import pytest

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.context_navigation import (
    LineageContextRouter,
)


def test_node_context_preserves_semantic_values_and_fills_claim_gaps() -> None:
    router = LineageContextRouter()

    context = router.node_context(
        "branch_001",
        base_context={
            "model_version_id": "mdl_explicit",
            "custom": "kept",
        },
        node_title="Experiment branch",
        node_status="local",
        claims=(
            ResourceClaim("model_version", "mdl_inherited", "read"),
            ResourceClaim("artifact_path", "/models/mdl_parent", "read"),
            ResourceClaim("training_run", "trn_parent", "read"),
            ResourceClaim("dataset", "Dataset A", "read"),
            ResourceClaim("profile", "Profile A", "read"),
            ResourceClaim("model_definition", "Qwen", "read"),
        ),
    )

    assert context == {
        "node_id": "branch_001",
        "node_title": "Experiment branch",
        "node_status": "local",
        "model_version_id": "mdl_explicit",
        "artifact_path": "/models/mdl_parent",
        "training_run_id": "trn_parent",
        "dataset_title": "Dataset A",
        "profile_title": "Profile A",
        "base_model": "Qwen",
        "custom": "kept",
    }


def test_node_context_is_immutable_after_construction() -> None:
    router = LineageContextRouter()
    source = {"model_version_id": "mdl_1"}
    context = router.node_context("snapshot", base_context=source)
    source["model_version_id"] = "mdl_changed"

    assert context["model_version_id"] == "mdl_1"
    with pytest.raises(TypeError):
        context["model_version_id"] = "mdl_evil"  # type: ignore[index]


def test_analysis_request_freezes_pair_and_exports_fresh_mutable_copy() -> None:
    router = LineageContextRouter()
    selected = {"model_version_id": "mdl_old"}
    current = {"model_version_id": "mdl_current"}
    request = router.request(
        "analysis",
        selected=selected,
        current=current,
    )
    selected["model_version_id"] = "mdl_mutated"

    first = request.mutable_payload()
    second = request.mutable_payload()

    assert first == {
        "selected": {"model_version_id": "mdl_old"},
        "current": {"model_version_id": "mdl_current"},
    }
    assert first is not second
    assert first["selected"] is not second["selected"]
    first_selected = first["selected"]
    assert isinstance(first_selected, dict)
    first_selected["model_version_id"] = "mdl_evil"
    assert request.mutable_payload()["selected"] == {
        "model_version_id": "mdl_old"
    }


def test_non_analysis_request_contains_only_selected_context() -> None:
    router = LineageContextRouter()

    request = router.request(
        "tests",
        selected={"model_version_id": "mdl_selected"},
        current={"model_version_id": "mdl_current"},
    )

    assert request.workspace_key == "tests"
    assert request.mutable_payload() == {
        "model_version_id": "mdl_selected"
    }
