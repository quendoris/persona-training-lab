from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any
from uuid import uuid4

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.datasets.status_mapping import (
    normalize_dataset_status,
)
from persona_training_lab.application.errors.reporter import (
    ApplicationErrorReporter,
)
from persona_training_lab.application.local_model.service import (
    LocalModelService,
)
from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
    normalize_local_model_status,
)
from persona_training_lab.application.messages import ActionResult, UserMessage
from persona_training_lab.application.ports.repositories import (
    TrainingReadRepositoryPort,
    TrainingWriteRepositoryPort,
)
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
    RuntimeOperationCoordinator,
    RuntimeOperationLease,
)
from persona_training_lab.application.training.full_backend import (
    LocalFullFineTuneBackend,
)
from persona_training_lab.application.training.status_mapping import (
    normalize_training_status,
)
from persona_training_lab.domain.datasets.statuses import (
    DatasetVersionStatus,
)
from persona_training_lab.domain.training.statuses import TrainingRunStatus


@dataclass(slots=True, frozen=True)
class TrainingRunSummary:
    run_id: str
    title: str
    subtitle: str
    status: str
    base_model: str
    profile: str
    dataset_version: str
    mode: str
    epoch_progress: str
    loss: str
    speed: str
    checkpoints_count: str
    progress: str = "0"
    artifact_path: str = ""
    error_message: str = ""
    status_code: TrainingRunStatus = TrainingRunStatus.UNKNOWN


@dataclass(slots=True, frozen=True)
class TrainingProfileOption:
    profile_id: str
    title: str


@dataclass(slots=True, frozen=True)
class TrainingDatasetOption:
    dataset_id: str
    title: str
    status: str
    status_code: DatasetVersionStatus = DatasetVersionStatus.UNKNOWN


class TrainingConfigurationError(ValueError):
    def __init__(
        self,
        *,
        code: str = "configuration_error",
    ) -> None:
        super().__init__(code)
        self.code = code


class TrainingValidationError(ValueError):
    def __init__(
        self,
        *,
        code: str = "validation_error",
    ) -> None:
        super().__init__(code)
        self.code = code


@dataclass(slots=True)
class TrainingService:
    training_repo: TrainingReadRepositoryPort | TrainingWriteRepositoryPort
    profiles_service: ProfilesService | None = None
    datasets_service: DatasetsService | None = None
    local_model_service: LocalModelService | None = None
    full_backend: LocalFullFineTuneBackend | None = None
    marker_backend: Any | None = None
    operation_coordinator: RuntimeOperationCoordinator | None = None
    error_reporter: ApplicationErrorReporter | None = None

    def list_training_runs(self) -> list[TrainingRunSummary]:
        rows = self.training_repo.list_training_runs()
        return [
            TrainingRunSummary(
                run_id=row.get("run_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                status=row.get("status", ""),
                base_model=row.get("base_model", ""),
                profile=row.get("profile", ""),
                dataset_version=row.get("dataset_version", ""),
                mode=row.get("mode", ""),
                epoch_progress=row.get("epoch_progress", ""),
                loss=row.get("loss", ""),
                speed=row.get("speed", ""),
                checkpoints_count=row.get("checkpoints_count", ""),
                progress=row.get("progress", "0"),
                artifact_path=row.get("artifact_path", ""),
                error_message=row.get("error_message", ""),
                status_code=normalize_training_status(
                    row.get("status", "")
                ),
            )
            for row in rows
        ]

    def list_training_run_logs(
        self,
        run_id: str,
        limit: int = 200,
    ) -> list[str]:
        lister = getattr(self.training_repo, "list_training_logs", None)
        if lister is None:
            return []
        return lister(run_id, limit)

    def list_profile_options(self) -> list[TrainingProfileOption]:
        if self.profiles_service is None:
            return []
        return [
            TrainingProfileOption(
                profile_id=item.profile_id,
                title=item.title,
            )
            for item in self.profiles_service.list_profiles()
        ]

    def list_dataset_options(self) -> list[TrainingDatasetOption]:
        if self.datasets_service is None:
            return []
        return [
            TrainingDatasetOption(
                dataset_id=item.dataset_id,
                title=item.title,
                status=item.status,
                status_code=normalize_dataset_status(item.status),
            )
            for item in self.datasets_service.list_datasets()
        ]

    def create_training_run(
        self,
        *,
        title: str,
        profile_id: str,
        dataset_id: str,
        base_model: str,
        epochs: int,
        batch_size: int,
        learning_rate: float,
    ) -> TrainingRunSummary:
        if epochs <= 0 or batch_size <= 0 or learning_rate <= 0:
            raise TrainingValidationError(code="invalid_hyperparameters")

        profiles = self.list_profile_options()
        selected_profile = next(
            (item for item in profiles if item.profile_id == profile_id),
            None,
        )
        if selected_profile is None:
            raise TrainingConfigurationError(code="profile_required")

        datasets = self.list_dataset_options()
        selected_dataset = next(
            (item for item in datasets if item.dataset_id == dataset_id),
            None,
        )
        if (
            selected_dataset is None
            or selected_dataset.status_code
            is not DatasetVersionStatus.APPROVED
        ):
            raise TrainingConfigurationError(code="dataset_required")

        if self.local_model_service is None:
            raise TrainingConfigurationError(code="model_required")
        model_probe = self.local_model_service.probe_model_files()
        if (
            normalize_local_model_status(model_probe.status)
            is not LocalModelStatus.FOUND
        ):
            raise TrainingConfigurationError(code="model_required")

        run_id = f"trn_{uuid4().hex[:8]}"
        normalized_title = title.strip() or f"Training run {run_id}"
        payload = {
            "id": run_id,
            "title": normalized_title,
            "subtitle": (
                f"{selected_profile.title} · {selected_dataset.title} · "
                f"{base_model.strip()} · epochs={epochs}, "
                f"batch={batch_size}, lr={learning_rate:g}"
            ),
            "status": "Готов к запуску",
            "base_model": (
                base_model.strip() or self.local_model_service.model_name
            ),
            "profile": selected_profile.title,
            "dataset_version": selected_dataset.title,
            "mode": "Full fine-tune",
            "epoch_progress": f"0 / {epochs}",
            "loss": "—",
            "speed": "—",
            "checkpoints_count": "00",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        create_method = getattr(
            self.training_repo,
            "create_training_run",
            None,
        )
        if create_method is None:
            raise RuntimeError(
                "Training write repository is not configured"
            )
        create_method(payload)
        return TrainingRunSummary(
            run_id=payload["id"],
            title=payload["title"],
            subtitle=payload["subtitle"],
            status=payload["status"],
            base_model=payload["base_model"],
            profile=payload["profile"],
            dataset_version=payload["dataset_version"],
            mode=payload["mode"],
            epoch_progress=payload["epoch_progress"],
            loss=payload["loss"],
            speed=payload["speed"],
            checkpoints_count=payload["checkpoints_count"],
            progress="0",
            artifact_path="",
            error_message="",
            status_code=TrainingRunStatus.READY,
        )

    def _parse_hparams(self, subtitle: str) -> tuple[int, int, float]:
        epochs = 1
        batch_size = 1
        learning_rate = 1e-4
        match = re.search(r"epochs=(\d+)", subtitle)
        if match:
            epochs = max(1, int(match.group(1)))
        match = re.search(r"batch=(\d+)", subtitle)
        if match:
            batch_size = max(1, int(match.group(1)))
        match = re.search(r"lr=([0-9.eE+-]+)", subtitle)
        if match:
            learning_rate = max(1e-8, float(match.group(1)))
        return epochs, batch_size, learning_rate

    def _set_runtime(self, run_id: str, payload: dict[str, str]) -> None:
        updater = getattr(
            self.training_repo,
            "update_training_run_runtime",
            None,
        )
        if updater is not None:
            updater(run_id, payload)

    def _log(
        self,
        run_id: str,
        message: str,
        level: str = "INFO",
    ) -> None:
        logger = getattr(self.training_repo, "add_training_log", None)
        if logger is not None:
            logger(run_id, level, message)

    def _begin_training_operation(
        self,
        run: dict[str, str],
    ) -> RuntimeOperationLease | None:
        if self.operation_coordinator is None:
            return None
        model_path = (
            self.local_model_service.model_path
            if self.local_model_service is not None
            else run.get("base_model", "")
        )
        return self.operation_coordinator.begin(
            operation_kind="training",
            subject_kind="training_run",
            subject_id=run.get("run_id", ""),
            claims=(
                ResourceClaim(
                    "training_run",
                    run.get("run_id", ""),
                    "write",
                ),
                ResourceClaim("model_path", model_path, "read"),
                ResourceClaim(
                    "dataset",
                    run.get("dataset_version", ""),
                    "read",
                ),
                ResourceClaim(
                    "profile",
                    run.get("profile", ""),
                    "read",
                ),
                # A local full fine-tune owns the training device. Other UI work
                # and read-only model inspection remain available.
                ResourceClaim(
                    "compute_device",
                    "local_training",
                    "write",
                ),
            ),
        )

    def start_full_finetune_run(self, run_id: str) -> ActionResult:
        get_run = getattr(self.training_repo, "get_training_run", None)
        if get_run is None:
            raise TrainingValidationError(code="start_failed")
        run = get_run(run_id)
        if run is None:
            raise TrainingValidationError(code="run_not_found")
        status_code = normalize_training_status(run.get("status", ""))
        if status_code is TrainingRunStatus.RUNNING:
            raise TrainingValidationError(code="already_running")
        if status_code is not TrainingRunStatus.READY:
            raise TrainingValidationError(code="not_ready")
        if self.full_backend is None:
            self._set_terminal_error(run, "backend_unavailable")
            return ActionResult(False, "backend_unavailable")
        if self.local_model_service is None:
            self._set_terminal_error(run, "model_missing")
            return ActionResult(False, "model_missing")

        lease: RuntimeOperationLease | None = None
        try:
            lease = self._begin_training_operation(run)
        except OperationConflictError as conflict:
            blocker = conflict.blockers[0] if conflict.blockers else None
            blocker_kind = (
                blocker.operation.operation_kind
                if blocker is not None
                else ""
            )
            technical_message = (
                "resource_busy"
                if not blocker_kind
                else f"resource_busy:{blocker_kind}"
            )
            self._log(run_id, technical_message, "WARNING")
            if self.error_reporter is not None:
                self.error_reporter.report_message(
                    "training.resource_busy",
                    component="training.start",
                    level="WARNING",
                    entity_kind="training_run",
                    entity_id=run_id,
                    context={
                        "blockers": [
                            item.message for item in conflict.blockers
                        ]
                    },
                )
            return ActionResult(
                False,
                "resource_busy",
                {"blocker_kind": blocker_kind},
            )

        epochs, batch_size, learning_rate = self._parse_hparams(
            run.get("subtitle", "")
        )
        started_at = datetime.now(timezone.utc).isoformat()
        operation_id = lease.operation_id if lease is not None else ""
        correlation_id = lease.correlation_id if lease is not None else ""

        try:
            self._set_runtime(
                run_id,
                {
                    "status": "Выполняется",
                    "epoch_progress": f"0 / {epochs}",
                    "progress": "0",
                    "loss": "ожидание метрики",
                    "speed": "ожидание метрики",
                    "checkpoints_count": "00",
                    "started_at": started_at,
                    "finished_at": "",
                    "artifact_path": "",
                    "error_message": "",
                },
            )
            self._log(run_id, "Запуск full fine-tune")
            self._log(
                run_id,
                "Параметры full fine-tune: "
                f"epochs={epochs}, batch={batch_size}, "
                f"lr={learning_rate:g}",
            )

            result = self.full_backend.run(
                run_id,
                self.local_model_service.model_path,
                "MIA_SENTINEL_FT_TEST_001",
                "MIA_FINE_TUNE_MARKER_OK_001",
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
            )

            self._log(run_id, result.message)
            self._log(
                run_id,
                "effective max_steps="
                f"{result.max_steps}, learning_rate="
                f"{result.learning_rate:g}, trainable_params="
                f"{result.trainable_params}",
            )
            self._log(
                run_id,
                f"initial_loss={result.initial_loss:.6f}, "
                f"final_loss={result.final_loss:.6f}",
            )
            if result.artifact_path:
                self._log(
                    run_id,
                    f"Artifact saved: {result.artifact_path}",
                )
                if lease is not None:
                    lease.attach(
                        ResourceClaim(
                            "artifact_path",
                            result.artifact_path,
                            "write",
                        )
                    )

            is_success = (
                normalize_training_status(result.status)
                is TrainingRunStatus.COMPLETED
            )
            self._set_runtime(
                run_id,
                {
                    "status": "Завершено" if is_success else "Ошибка",
                    "epoch_progress": (
                        f"{epochs} / {epochs}"
                        if is_success
                        else f"0 / {epochs}"
                    ),
                    "progress": "1.0" if is_success else "0",
                    "loss": (
                        f"{result.final_loss:.6f}"
                        if result.final_loss
                        else "—"
                    ),
                    "speed": "full fine-tune",
                    "checkpoints_count": (
                        "01" if result.artifact_path else "00"
                    ),
                    "started_at": started_at,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "artifact_path": result.artifact_path,
                    "error_message": (
                        "" if is_success else "backend_failed"
                    ),
                },
            )
            if lease is not None:
                if is_success:
                    lease.succeed()
                else:
                    lease.fail("backend_failed")
            if is_success:
                return ActionResult(
                    True,
                    "completed",
                    {"artifact": result.artifact_path},
                )
            return ActionResult(
                False,
                "start_failed",
                {"backend_status": result.status},
            )
        except Exception as error:
            report = None
            if self.error_reporter is not None:
                report = self.error_reporter.capture(
                    error,
                    component="training.full_finetune",
                    user_message=UserMessage(
                        "error.training.full_finetune.safe_stop"
                    ),
                    entity_kind="training_run",
                    entity_id=run_id,
                    operation_id=operation_id,
                    correlation_id=correlation_id,
                    context={
                        "epochs": epochs,
                        "batch_size": batch_size,
                        "learning_rate": learning_rate,
                    },
                )
            error_id = report.error_id if report is not None else ""
            technical_message = (
                "safe_stop" if not error_id else f"safe_stop:{error_id}"
            )
            self._log(run_id, technical_message, "ERROR")
            self._set_runtime(
                run_id,
                {
                    "status": "Ошибка",
                    "epoch_progress": f"0 / {epochs}",
                    "progress": "0",
                    "loss": "—",
                    "speed": "—",
                    "checkpoints_count": "00",
                    "started_at": started_at,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "artifact_path": "",
                    "error_message": technical_message,
                },
            )
            if lease is not None:
                lease.fail(technical_message)
            return ActionResult(
                False,
                "safe_stop",
                {"error_id": error_id},
            )
        finally:
            if lease is not None and not lease.closed:
                lease.fail("operation_without_terminal_status")

    def _set_terminal_error(
        self,
        run: dict[str, str],
        message: str,
    ) -> None:
        self._set_runtime(
            run.get("run_id", ""),
            {
                "status": "Ошибка",
                "epoch_progress": run.get("epoch_progress", "—"),
                "progress": "0",
                "loss": "—",
                "speed": "—",
                "checkpoints_count": "00",
                "started_at": "",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "artifact_path": "",
                "error_message": message,
            },
        )

    def start_real_or_skeleton_run(self, run_id: str) -> ActionResult:
        return self.start_full_finetune_run(run_id)

    def start_training_run(self, run_id: str) -> None:
        self.start_full_finetune_run(run_id)

    def advance_training_run(self, run_id: str) -> bool:
        run = getattr(
            self.training_repo,
            "get_training_run",
            lambda _id: None,
        )(run_id)
        return bool(
            run
            and normalize_training_status(run.get("status"))
            is not TrainingRunStatus.RUNNING
        )

    def run_marker_finetune_smoke(
        self,
        run_id: str,
    ) -> tuple[str, str]:
        return "Training backend не подключён", ""
