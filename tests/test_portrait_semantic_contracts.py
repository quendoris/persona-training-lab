from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.application.experiments.portrait import (
    CASE_HEADER_RE as PORTRAIT_CASE_HEADER_RE,
    SCORE_RE as PORTRAIT_SCORE_RE,
    parse_portrait_payload,
)
from persona_training_lab.application.experiments.service import (
    ExperimentsService,
)
from persona_training_lab.application.experiments.status_mapping import (
    normalize_evaluation_status,
)
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)
from persona_training_lab.ui.viewmodels.agents import (
    CASE_HEADER_RE as COMPAT_CASE_HEADER_RE,
    SCORE_RE as COMPAT_SCORE_RE,
)


PORTRAIT = (
    "PORTRAIT: 2/3 Big Five items · snapshot=Mia v1 · "
    "model_version=mdl_001 · artifact=/models/mdl_001 · "
    "battery=v1 · scoring=s1\n\n"
    "CASE 1\nTRAIT: Extraversion\nKEY: E1\nREVERSE: 0\n"
    "ITEM: Starts conversations.\nSTATUS: Model responds\n"
    "VALID_SCORE: 1\nRAW_RESPONSE: SCORE: 4\nRESPONSE: SCORE: 4\n\n"
    "CASE 2\nTRAIT: Extraversion\nKEY: E2R\nREVERSE: 1\n"
    "ITEM: Stays outside conversations.\nSTATUS: Модель отвечает\n"
    "VALID_SCORE: 1\nRAW_RESPONSE: SCORE: 2\nRESPONSE: SCORE: 2\n\n"
    "CASE 3\nTRAIT: Agreeableness\nKEY: A1\nREVERSE: 0\n"
    "ITEM: Considers the other person.\nSTATUS: generation failed\n"
    "VALID_SCORE: 0\nRAW_RESPONSE: INVALID\nRESPONSE: INVALID"
)


def test_portrait_payload_is_parsed_once_into_semantic_records() -> None:
    assert COMPAT_CASE_HEADER_RE is PORTRAIT_CASE_HEADER_RE
    assert COMPAT_SCORE_RE is PORTRAIT_SCORE_RE

    portrait = parse_portrait_payload(PORTRAIT)

    assert (portrait.passed, portrait.total) == (2, 3)
    assert portrait.model_version_id == "mdl_001"
    assert portrait.artifact_path == "/models/mdl_001"
    assert len(portrait.cases) == 3
    assert portrait.cases[0].score == 4
    assert portrait.cases[1].adjusted_score == 4
    assert portrait.invalid_count == 1
    assert portrait.trait_scores() == {"Extraversion": 4.0}


def test_evaluation_statuses_accept_legacy_and_semantic_values() -> None:
    assert (
        normalize_evaluation_status("Портрет собран")
        is EvaluationRunStatus.COMPLETED
    )
    assert (
        normalize_evaluation_status("completed")
        is EvaluationRunStatus.COMPLETED
    )
    assert (
        normalize_evaluation_status("Есть ошибки · 1 invalid")
        is EvaluationRunStatus.PARTIAL
    )
    assert (
        normalize_evaluation_status(EvaluationRunStatus.RUNNING)
        is EvaluationRunStatus.RUNNING
    )


class _Repo:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []

    def list_experiments(self):
        return list(reversed(self.rows))

    def create_experiment(self, payload):
        self.rows.append(dict(payload))


class _EnglishLocalModel:
    model_path = "/models/base"

    def probe_model_files_at(self, _path: str):
        return SimpleNamespace(status="Model found", details="ok")

    def generate_at(self, _path: str, _prompt: str, instruction_prompt=None):
        return SimpleNamespace(
            status="Model responds",
            message="ok",
            response="SCORE: 4",
        )


def test_new_portrait_rows_store_semantic_status_not_ui_language() -> None:
    repo = _Repo()
    service = ExperimentsService(
        experiments_repo=repo,
        local_model_service=_EnglishLocalModel(),
    )

    result = service.run_personality_portrait_test_pack()

    assert result.ok is True
    assert result.message_code == "portrait_completed"
    assert repo.rows[0]["status"] == EvaluationRunStatus.COMPLETED.value
    assert "snapshot=unregistered" in repo.rows[0]["subtitle"]
    summary = service.list_experiments()[0]
    assert summary.status_code is EvaluationRunStatus.COMPLETED
