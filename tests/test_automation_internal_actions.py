from __future__ import annotations

import json
from pathlib import Path

from persona_training_lab.application.automation.ptl_actions import (
    _parse_learning_rates,
)
from persona_training_lab.bootstrap.wiring import build_container
from persona_training_lab.config.app_settings import AppSettings


def test_production_automation_exposes_and_runs_internal_ptl_actions(
    tmp_path: Path,
) -> None:
    container = build_container(
        AppSettings(workspace_dir=tmp_path / "workspace")
    )
    try:
        recipes = container.automation_vm.recipes()
        ids = {item.recipe_id for item in recipes}

        assert "workspace_health" in ids
        assert "ptl.model.probe" in ids
        assert "ptl.profile.create" in ids
        assert "ptl.analysis.compare" in ids
        assert "ptl.training.sweep" in ids
        assert "ptl.acceptance.run" in ids

        created = container.automation_vm.run_recipe(
            "ptl.profile.create",
            {
                "title": "Automation Profile",
                "description": "Created through internal Automation.",
                "communication_style": "Precise.",
                "principles": "Preserve provenance.",
                "constraints": "Do not invent facts.",
                "notes": "integration test",
            },
        )

        assert created.ok is True
        assert created.effect_scope == "ptl_internal"
        payload = json.loads(created.stdout)
        assert payload["schema"] == "ptl:automation-action-output:v1"
        assert payload["action"] == "profile.create"
        assert payload["code"] == "created"
        profile = payload["payload"]["profile"]
        assert profile["title"] == "Automation Profile"

        snapshot = container.automation_vm.run_recipe(
            "ptl.state.snapshot"
        )
        assert snapshot.ok is True
        state = json.loads(snapshot.stdout)["payload"]
        assert any(
            item["profile_id"] == profile["profile_id"]
            for item in state["profiles"]
        )
        lineage = state["lineage_projection"]
        assert lineage["nodes"] == []
        assert lineage["edges"] == []
        assert lineage["source_failures"] == []

        operations = container.primary_connection.execute(
            """
            SELECT operation_kind, state
            FROM runtime_operations
            ORDER BY started_at ASC
            """
        ).fetchall()
        assert operations
        assert all(row["state"] == "succeeded" for row in operations)
        assert all(
            row["operation_kind"] == "automation_action"
            for row in operations
        )
    finally:
        container.close()


def test_training_sweep_learning_rate_parser() -> None:
    assert _parse_learning_rates(
        "0.0001, 3e-5, 1e-5, 0.000003"
    ) == (
        0.0001,
        0.00003,
        0.00001,
        0.000003,
    )


def test_training_sweep_learning_rate_parser_rejects_invalid_values() -> None:
    for value in ("", "0", "-1e-5", "abc"):
        try:
            _parse_learning_rates(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {value!r}")
