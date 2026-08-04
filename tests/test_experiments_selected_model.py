from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.application.experiments.service import ExperimentsService


class _Repo:
    def __init__(self) -> None:
        self.created: list[dict[str, str]] = []

    def list_experiments(self):
        return list(reversed(self.created))

    def create_experiment(self, payload):
        self.created.append(dict(payload))


class _LocalModel:
    model_path = "/models/base"

    def __init__(self) -> None:
        self.probed: list[str] = []
        self.generated: list[str] = []

    def probe_model_files_at(self, path: str):
        self.probed.append(path)
        return SimpleNamespace(status="Модель найдена", details="ok")

    def generate_at(self, path: str, prompt: str, instruction_prompt=None):
        self.generated.append(path)
        return SimpleNamespace(
            status="Модель отвечает",
            message="ok",
            response="SCORE: 4",
        )


class _Versions:
    def list_model_versions(self):
        return [
            SimpleNamespace(
                version_id="mdl_new",
                title="New",
                artifact_path="/models/new",
            ),
            SimpleNamespace(
                version_id="mdl_old",
                title="Old",
                artifact_path="/models/old",
            ),
        ]


def test_portrait_runs_against_requested_weight_artifact() -> None:
    repo = _Repo()
    model = _LocalModel()
    service = ExperimentsService(
        experiments_repo=repo,
        local_model_service=model,
        model_versions_service=_Versions(),
    )

    result = service.run_personality_portrait_test_pack("mdl_old")

    assert result.ok is True
    assert model.probed == ["/models/old"]
    assert model.generated
    assert set(model.generated) == {"/models/old"}
    assert "model_version=mdl_old" in repo.created[0]["subtitle"]
    assert "artifact=/models/old" in repo.created[0]["subtitle"]


def test_unknown_requested_version_fails_without_using_latest() -> None:
    repo = _Repo()
    model = _LocalModel()
    service = ExperimentsService(
        experiments_repo=repo,
        local_model_service=model,
        model_versions_service=_Versions(),
    )

    result = service.run_personality_portrait_test_pack("mdl_missing")

    assert result.ok is False
    assert "mdl_missing" in result.message
    assert model.probed == []
    assert model.generated == []
    assert repo.created == []
