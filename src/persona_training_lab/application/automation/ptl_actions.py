from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from persona_training_lab.application.agents.service import AgentsService
from persona_training_lab.application.analysis.portrait_pair import (
    compare_portrait_payloads,
)
from persona_training_lab.application.analysis.service import AnalysisService
from persona_training_lab.application.automation.service import (
    AutomationInternalActionResult,
)
from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.experiments.portrait import (
    parse_portrait_payload,
)
from persona_training_lab.application.experiments.service import (
    ExperimentsService,
)
from persona_training_lab.application.local_model.service import (
    LocalModelService,
)
from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
    normalize_local_model_status,
)
from persona_training_lab.application.lineage.projection import (
    LineageEntityKind,
    LineageProjectionService,
    LineageRelation,
    lineage_node_id,
)
from persona_training_lab.application.model_versions.service import (
    ModelVersionsService,
)
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.projects.service import ProjectsService
from persona_training_lab.application.style.service import (
    StylePreferencesService,
)
from persona_training_lab.application.training.service import (
    TrainingConfigurationError,
    TrainingService,
    TrainingValidationError,
)
from persona_training_lab.domain.datasets.statuses import (
    DatasetVersionStatus,
)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


@dataclass(slots=True)
class PTLAutomationActionRunner:
    local_model_service: LocalModelService
    profiles_service: ProfilesService
    datasets_service: DatasetsService
    training_service: TrainingService
    model_versions_service: ModelVersionsService
    experiments_service: ExperimentsService
    analysis_service: AnalysisService
    agents_service: AgentsService | None = None
    projects_service: ProjectsService | None = None
    style_service: StylePreferencesService | None = None

    def run(
        self,
        action_id: str,
        inputs: Mapping[str, str],
        *,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> AutomationInternalActionResult:
        if cancel_requested is not None and cancel_requested():
            return AutomationInternalActionResult(False, "cancelled")

        actions = {
            "model.probe": self._model_probe,
            "model.generate": self._model_generate,
            "profile.create": self._profile_create,
            "dataset.import": self._dataset_import,
            "dataset.validate": self._dataset_validate,
            "dataset.approve": self._dataset_approve,
            "training.create": self._training_create,
            "training.start": self._training_start,
            "model_versions.list": self._model_versions_list,
            "experiment.portrait": self._experiment_portrait,
            "analysis.compare": self._analysis_compare,
            "state.snapshot": self._state_snapshot,
            "acceptance.run": self._acceptance_run,
        }
        handler = actions.get(action_id)
        if handler is None:
            return AutomationInternalActionResult(
                False,
                "action_not_found",
                {"action_id": action_id},
            )
        try:
            return handler(inputs)
        except (
            TrainingConfigurationError,
            TrainingValidationError,
        ) as exc:
            return AutomationInternalActionResult(
                False,
                exc.code,
                {"action_id": action_id},
            )
        except Exception as exc:
            return AutomationInternalActionResult(
                False,
                "action_failed",
                {"action_id": action_id},
                f"{type(exc).__name__}: {exc}",
            )

    def _model_probe(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        reference = (
            inputs.get("model_path", "").strip()
            or self.local_model_service.model_name
        )
        path = self.local_model_service.resolve_model_path(reference)
        files = self.local_model_service.probe_model_files_at(path)
        file_status = normalize_local_model_status(files.status)
        if file_status is not LocalModelStatus.FOUND:
            return AutomationInternalActionResult(
                False,
                "model_not_ready",
                {
                    "model_path": path,
                    "file_status": file_status.value,
                    "file_diagnostic": _jsonable(files.diagnostic),
                    "backend_message": "",
                    "backend_diagnostic": None,
                },
            )

        backend = self.local_model_service.probe_inference_backend_at(path)
        backend_code = (
            backend.diagnostic.code
            if backend.diagnostic is not None
            else ""
        )
        ok = backend_code == "inference_runtime_ready"
        return AutomationInternalActionResult(
            ok,
            "model_ready" if ok else "model_not_ready",
            {
                "model_path": path,
                "file_status": file_status.value,
                "file_diagnostic": _jsonable(files.diagnostic),
                "backend_message": backend.message,
                "backend_diagnostic": _jsonable(backend.diagnostic),
            },
        )

    def _model_generate(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        reference = (
            inputs.get("model_path", "").strip()
            or self.local_model_service.model_name
        )
        prompt = inputs.get("prompt", "").strip()
        instruction = inputs.get("instruction", "").strip() or None
        if not prompt:
            return AutomationInternalActionResult(
                False,
                "input_required",
                {"inputs": ["prompt"]},
            )
        path = self.local_model_service.resolve_model_path(reference)
        result = self.local_model_service.generate_at(
            path,
            prompt,
            instruction_prompt=instruction,
        )
        status = normalize_local_model_status(result.status)
        return AutomationInternalActionResult(
            status is LocalModelStatus.RESPONDING,
            (
                "model_responded"
                if status is LocalModelStatus.RESPONDING
                else "model_generate_failed"
            ),
            {
                "model_path": path,
                "status": status.value,
                "message": result.message,
                "response": result.response,
                "diagnostic": _jsonable(result.diagnostic),
            },
        )

    def _profile_create(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        result, profile = self.profiles_service.create_profile(
            title=inputs.get("title", ""),
            description=inputs.get("description", ""),
            communication_style=inputs.get("communication_style", ""),
            principles=inputs.get("principles", ""),
            constraints=inputs.get("constraints", ""),
            notes=inputs.get("notes", ""),
        )
        return AutomationInternalActionResult(
            result.ok,
            result.code,
            {
                "result": _jsonable(result),
                "profile": _jsonable(profile),
            },
        )

    def _dataset_import(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        path = inputs.get("path", "").strip()
        if not path:
            return AutomationInternalActionResult(
                False,
                "input_required",
                {"inputs": ["path"]},
            )
        dataset = self.datasets_service.add_dataset_from_path(path)
        return AutomationInternalActionResult(
            True,
            "dataset_imported",
            {"dataset": _jsonable(dataset)},
        )

    def _dataset_validate(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        dataset_id = inputs.get("dataset_id", "").strip()
        result = self.datasets_service.validate_dataset(dataset_id)
        ok = (
            result.status == DatasetVersionStatus.VALIDATED.value
            and result.invalid_rows == 0
        )
        return AutomationInternalActionResult(
            ok,
            "dataset_validated" if ok else "dataset_invalid",
            {"validation": _jsonable(result)},
        )

    def _dataset_approve(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        dataset_id = inputs.get("dataset_id", "").strip()
        result = self.datasets_service.approve_dataset(dataset_id)
        dataset = next(
            (
                item
                for item in self.datasets_service.list_datasets()
                if item.dataset_id == dataset_id
            ),
            None,
        )
        return AutomationInternalActionResult(
            result.ok,
            result.code,
            {
                "result": _jsonable(result),
                "dataset": _jsonable(dataset),
            },
        )

    def _training_create(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        run = self.training_service.create_training_run(
            title=inputs.get("title", "").strip() or "Automation training",
            profile_id=inputs.get("profile_id", "").strip(),
            dataset_id=inputs.get("dataset_id", "").strip(),
            base_model=(
                inputs.get("base_model", "").strip()
                or self.local_model_service.model_name
            ),
            epochs=int(inputs.get("epochs", "1") or "1"),
            batch_size=int(inputs.get("batch_size", "1") or "1"),
            learning_rate=float(
                inputs.get("learning_rate", "0.0001") or "0.0001"
            ),
        )
        return AutomationInternalActionResult(
            True,
            "training_created",
            {"training_run": _jsonable(run)},
        )

    def _training_start(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        run_id = inputs.get("run_id", "").strip()
        result = self.training_service.start_real_or_skeleton_run(run_id)
        run = next(
            (
                item
                for item in self.training_service.list_training_runs()
                if item.run_id == run_id
            ),
            None,
        )
        version = next(
            (
                item
                for item in self.model_versions_service.list_model_versions()
                if item.training_run_id == run_id
            ),
            None,
        )
        return AutomationInternalActionResult(
            result.ok,
            result.code,
            {
                "result": _jsonable(result),
                "training_run": _jsonable(run),
                "model_version": _jsonable(version),
                "logs": self.training_service.list_training_run_logs(run_id),
            },
        )

    def _model_versions_list(
        self,
        _inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        return AutomationInternalActionResult(
            True,
            "model_versions_listed",
            {
                "model_versions": _jsonable(
                    self.model_versions_service.list_model_versions()
                )
            },
        )

    def _experiment_portrait(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        version_id = inputs.get("model_version_id", "").strip() or None
        result = self.experiments_service.run_personality_portrait_test_pack(
            version_id
        )
        experiment = next(
            (
                item
                for item in self.experiments_service.list_experiments()
                if item.experiment_id == result.experiment_id
            ),
            None,
        )
        portrait = (
            parse_portrait_payload(experiment.subtitle)
            if experiment is not None
            else None
        )
        return AutomationInternalActionResult(
            result.ok,
            result.message_code or result.message,
            {
                "result": _jsonable(result),
                "experiment": _jsonable(experiment),
                "portrait": (
                    {
                        "passed": portrait.passed,
                        "total": portrait.total,
                        "model_version_id": portrait.model_version_id,
                        "artifact_path": portrait.artifact_path,
                        "battery_version": portrait.battery_version,
                        "scoring_version": portrait.scoring_version,
                        "trait_scores": portrait.trait_scores(),
                    }
                    if portrait is not None
                    else None
                ),
            },
        )

    def _analysis_compare(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        left_id = inputs.get("left_experiment_id", "").strip()
        right_id = inputs.get("right_experiment_id", "").strip()
        if not left_id or not right_id:
            return AutomationInternalActionResult(
                False,
                "input_required",
                {
                    "inputs": [
                        name
                        for name, value in (
                            ("left_experiment_id", left_id),
                            ("right_experiment_id", right_id),
                        )
                        if not value
                    ]
                },
            )

        experiments = {
            item.experiment_id: item
            for item in self.experiments_service.list_portrait_experiments()
        }
        left = experiments.get(left_id)
        right = experiments.get(right_id)
        if left is None or right is None:
            return AutomationInternalActionResult(
                False,
                "experiment_not_found",
                {
                    "left_experiment_id": left_id,
                    "right_experiment_id": right_id,
                },
            )

        comparison = compare_portrait_payloads(
            left.subtitle,
            right.subtitle,
        )
        return AutomationInternalActionResult(
            comparison.comparable,
            comparison.reason_code,
            {
                "left_experiment_id": left_id,
                "right_experiment_id": right_id,
                "protocol": (
                    list(comparison.protocol_key)
                    if comparison.protocol_key is not None
                    else None
                ),
                "complete": comparison.complete,
                "left_scores": comparison.left.trait_scores(),
                "right_scores": comparison.right.trait_scores(),
                "deltas": dict(comparison.deltas),
            },
        )

    def _state_snapshot(
        self,
        _inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        portrait_runs = []
        for experiment in self.experiments_service.list_portrait_experiments():
            record = parse_portrait_payload(experiment.subtitle)
            portrait_runs.append(
                {
                    "experiment_id": experiment.experiment_id,
                    "status": experiment.status,
                    "status_code": experiment.status_code.value,
                    "model_version_id": record.model_version_id,
                    "artifact_path": record.artifact_path,
                    "battery_version": record.battery_version,
                    "scoring_version": record.scoring_version,
                    "passed": record.passed,
                    "total": record.total,
                    "trait_scores": record.trait_scores(),
                }
            )

        lineage = LineageProjectionService(
            datasets_service=self.datasets_service,
            training_service=self.training_service,
            model_versions_service=self.model_versions_service,
            experiments_service=self.experiments_service,
        ).build_projection()

        payload: dict[str, object] = {
            "profiles": _jsonable(self.profiles_service.list_profiles()),
            "datasets": _jsonable(self.datasets_service.list_datasets()),
            "training_runs": _jsonable(
                self.training_service.list_training_runs()
            ),
            "model_versions": _jsonable(
                self.model_versions_service.list_model_versions()
            ),
            "experiments": _jsonable(
                self.experiments_service.list_experiments()
            ),
            "portrait_runs": portrait_runs,
            "analysis_results": _jsonable(
                self.analysis_service.list_analysis_results()
            ),
            "lineage_projection": _jsonable(lineage),
        }
        if self.agents_service is not None:
            payload["agents"] = _jsonable(self.agents_service.list_agents())
        if self.projects_service is not None:
            payload["projects"] = _jsonable(
                self.projects_service.list_projects()
            )
        if self.style_service is not None:
            payload["style_preferences"] = _jsonable(
                self.style_service.load_preferences()
            )
        return AutomationInternalActionResult(
            True,
            "state_snapshot",
            payload,
        )

    def _acceptance_run(
        self,
        inputs: Mapping[str, str],
    ) -> AutomationInternalActionResult:
        if self.model_versions_service.list_model_versions():
            return AutomationInternalActionResult(
                False,
                "acceptance_requires_clean_workspace",
                {"reason": "model_versions_not_empty"},
            )
        if self.training_service.list_training_runs():
            return AutomationInternalActionResult(
                False,
                "acceptance_requires_clean_workspace",
                {"reason": "training_runs_not_empty"},
            )
        if self.experiments_service.list_experiments():
            return AutomationInternalActionResult(
                False,
                "acceptance_requires_clean_workspace",
                {"reason": "experiments_not_empty"},
            )

        probe = self._model_probe(inputs)
        if not probe.ok:
            return probe
        generated = self._model_generate(inputs)
        if not generated.ok:
            return generated

        profile_title = (
            inputs.get("profile_title", "").strip()
            or "Acceptance Neutral v1"
        )
        existing_profile = next(
            (
                item
                for item in self.profiles_service.list_profiles()
                if item.title == profile_title
            ),
            None,
        )
        if existing_profile is None:
            created = self._profile_create(
                {
                    "title": profile_title,
                    "description": (
                        inputs.get("profile_description", "").strip()
                        or "Neutral automated release-acceptance profile."
                    ),
                    "communication_style": (
                        inputs.get("communication_style", "").strip()
                        or "Follow the supplied training examples."
                    ),
                    "principles": (
                        inputs.get("principles", "").strip()
                        or "Remain internally consistent."
                    ),
                    "constraints": (
                        inputs.get("constraints", "").strip()
                        or "Do not invent unavailable facts."
                    ),
                    "notes": "Created by PTL internal acceptance automation.",
                }
            )
            if not created.ok:
                return created
            profile_payload = created.payload.get("profile")
            profile_id = (
                str(profile_payload.get("profile_id", ""))
                if isinstance(profile_payload, Mapping)
                else ""
            )
        else:
            profile_id = existing_profile.profile_id

        dataset_path = inputs.get("dataset_path", "").strip()
        if not dataset_path:
            return AutomationInternalActionResult(
                False,
                "input_required",
                {"inputs": ["dataset_path"]},
            )
        resolved_dataset = str(Path(dataset_path).expanduser().resolve())
        existing_dataset = next(
            (
                item
                for item in self.datasets_service.list_datasets()
                if str(Path(item.path).expanduser().resolve())
                == resolved_dataset
            ),
            None,
        )
        if existing_dataset is None:
            imported = self._dataset_import({"path": resolved_dataset})
            if not imported.ok:
                return imported
            dataset_payload = imported.payload.get("dataset")
            dataset_id = (
                str(dataset_payload.get("dataset_id", ""))
                if isinstance(dataset_payload, Mapping)
                else ""
            )
        else:
            dataset_id = existing_dataset.dataset_id

        validated = self._dataset_validate({"dataset_id": dataset_id})
        if not validated.ok:
            return validated
        approved = self._dataset_approve({"dataset_id": dataset_id})
        if not approved.ok:
            return approved

        baseline = self._experiment_portrait({})
        if not baseline.ok:
            return AutomationInternalActionResult(
                False,
                "baseline_portrait_failed",
                {"baseline": dict(baseline.payload)},
                baseline.error,
            )

        created_run = self._training_create(
            {
                "title": (
                    inputs.get("training_title", "").strip()
                    or "PTL automated acceptance"
                ),
                "profile_id": profile_id,
                "dataset_id": dataset_id,
                "base_model": (
                    inputs.get("model_path", "").strip()
                    or self.local_model_service.model_name
                ),
                "epochs": inputs.get("epochs", "1"),
                "batch_size": inputs.get("batch_size", "1"),
                "learning_rate": inputs.get(
                    "learning_rate",
                    "0.0001",
                ),
            }
        )
        if not created_run.ok:
            return created_run
        run_payload = created_run.payload.get("training_run")
        run_id = (
            str(run_payload.get("run_id", ""))
            if isinstance(run_payload, Mapping)
            else ""
        )

        trained = self._training_start({"run_id": run_id})
        if not trained.ok:
            return trained
        version_payload = trained.payload.get("model_version")
        version_id = (
            str(version_payload.get("version_id", ""))
            if isinstance(version_payload, Mapping)
            else ""
        )
        if not version_id:
            return AutomationInternalActionResult(
                False,
                "model_version_missing",
                {"training": dict(trained.payload)},
            )

        post = self._experiment_portrait(
            {"model_version_id": version_id}
        )
        if not post.ok:
            return AutomationInternalActionResult(
                False,
                "post_portrait_failed",
                {"post": dict(post.payload)},
                post.error,
            )

        baseline_portrait = baseline.payload.get("portrait")
        post_portrait = post.payload.get("portrait")
        if isinstance(baseline_portrait, Mapping):
            if not (
                int(baseline_portrait.get("passed", 0))
                == int(baseline_portrait.get("total", 0))
                == 10
            ):
                return AutomationInternalActionResult(
                    False,
                    "baseline_portrait_incomplete",
                    {"baseline": dict(baseline.payload)},
                )
        if isinstance(post_portrait, Mapping):
            if not (
                int(post_portrait.get("passed", 0))
                == int(post_portrait.get("total", 0))
                == 10
            ):
                return AutomationInternalActionResult(
                    False,
                    "post_portrait_incomplete",
                    {"post": dict(post.payload)},
                )

        baseline_experiment = baseline.payload.get("experiment")
        post_experiment = post.payload.get("experiment")
        if not (
            isinstance(baseline_experiment, Mapping)
            and isinstance(post_experiment, Mapping)
        ):
            return AutomationInternalActionResult(
                False,
                "analysis_pair_missing",
                {
                    "baseline": dict(baseline.payload),
                    "post": dict(post.payload),
                },
            )

        comparison = compare_portrait_payloads(
            str(baseline_experiment.get("subtitle", "")),
            str(post_experiment.get("subtitle", "")),
        )
        if not comparison.comparable:
            return AutomationInternalActionResult(
                False,
                f"analysis_{comparison.reason_code}",
                {
                    "baseline": dict(baseline.payload),
                    "post": dict(post.payload),
                },
            )

        lineage = LineageProjectionService(
            datasets_service=self.datasets_service,
            training_service=self.training_service,
            model_versions_service=self.model_versions_service,
            experiments_service=self.experiments_service,
        ).build_projection()
        post_experiment_id = str(
            post_experiment.get("experiment_id", "")
        ).strip()
        run_node_id = lineage_node_id(
            LineageEntityKind.TRAINING_RUN,
            run_id,
        )
        version_node_id = lineage_node_id(
            LineageEntityKind.MODEL_VERSION,
            version_id,
        )
        evaluation_node_id = lineage_node_id(
            LineageEntityKind.EVALUATION_RUN,
            post_experiment_id,
        )
        lineage_edges = set(lineage.edges)
        expected_edges = {
            (
                run_node_id,
                version_node_id,
                LineageRelation.PRODUCES_VERSION,
            ),
            (
                version_node_id,
                evaluation_node_id,
                LineageRelation.EVALUATES_VERSION,
            ),
        }
        observed_edges = {
            (
                edge.source_node_id,
                edge.target_node_id,
                edge.relation,
            )
            for edge in lineage_edges
        }
        if not expected_edges.issubset(observed_edges):
            return AutomationInternalActionResult(
                False,
                "lineage_projection_incomplete",
                {
                    "run_id": run_id,
                    "model_version_id": version_id,
                    "post_experiment_id": post_experiment_id,
                    "projection": _jsonable(lineage),
                },
            )

        return AutomationInternalActionResult(
            True,
            "acceptance_completed",
            {
                "model_probe": dict(probe.payload),
                "model_generate": dict(generated.payload),
                "profile_id": profile_id,
                "dataset_id": dataset_id,
                "baseline": dict(baseline.payload),
                "training": dict(trained.payload),
                "model_version_id": version_id,
                "post": dict(post.payload),
                "analysis": {
                    "protocol": list(comparison.protocol_key or ()),
                    "complete": comparison.complete,
                    "trait_deltas": dict(comparison.deltas),
                },
                "lineage": {
                    "topology_revision": lineage.topology_revision,
                    "content_revision": lineage.content_revision,
                    "expected_edges_present": True,
                    "source_failures": _jsonable(
                        lineage.source_failures
                    ),
                },
            },
        )
