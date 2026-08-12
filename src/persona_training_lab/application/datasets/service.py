from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from persona_training_lab.application.datasets.diagnostics import (
    DatasetDiagnostic,
    dataset_diagnostic,
    encode_dataset_diagnostic,
)
from persona_training_lab.application.datasets.errors import (
    DatasetServiceError,
    DatasetServiceErrorCode,
)
from persona_training_lab.application.messages import ActionResult
from persona_training_lab.application.ports.repositories import DatasetsRepositoryPort
from persona_training_lab.domain.datasets.statuses import (
    DatasetReadinessStatus,
    DatasetVersionStatus,
)


@dataclass(slots=True, frozen=True)
class DatasetSummary:
    dataset_id: str
    title: str
    subtitle: str
    status: str
    record_count: int
    valid_count: int
    invalid_count: int
    quality_summary: str
    validation_errors_preview: str
    path: str
    format: str


@dataclass(slots=True, frozen=True)
class DatasetValidationResult:
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    warning_count: int
    errors_preview: tuple[DatasetDiagnostic, ...]


@dataclass(slots=True, frozen=True)
class DatasetPreviewRecord:
    row_id: str
    input_summary: str | DatasetDiagnostic
    traits: str
    quality: str


@dataclass(slots=True)
class DatasetsService:
    datasets_repo: DatasetsRepositoryPort

    def list_datasets(self) -> list[DatasetSummary]:
        return [self._row_to_summary(row) for row in self.datasets_repo.list_datasets()]

    def add_dataset_from_path(self, file_path: str) -> DatasetSummary:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise DatasetServiceError(DatasetServiceErrorCode.FILE_NOT_FOUND)
        if path.suffix.lower() != ".jsonl":
            raise DatasetServiceError(DatasetServiceErrorCode.ONLY_JSONL)

        now = datetime.now(timezone.utc).isoformat()
        dataset_id = f"ds_{uuid4().hex[:8]}"
        self.datasets_repo.add_dataset(
            {
                "id": dataset_id,
                "title": path.stem,
                "subtitle": "",
                "path": str(path),
                "format": "jsonl",
                "status": DatasetVersionStatus.IMPORTED.value,
                "record_count": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "quality_summary": "",
                "validation_errors_preview": "",
                "linked_profile": "—",
                "readiness": DatasetReadinessStatus.AWAITING_VALIDATION.value,
                "schema_name": "jsonl_finetune_v1",
                "created_at": now,
                "updated_at": now,
            }
        )
        created = self.datasets_repo.get_dataset(dataset_id)
        if created is None:
            raise DatasetServiceError(DatasetServiceErrorCode.SAVE_FAILED)
        return self._row_to_summary(created)

    def validate_dataset(self, dataset_id: str) -> DatasetValidationResult:
        row = self.datasets_repo.get_dataset(dataset_id)
        if row is None:
            raise DatasetServiceError(DatasetServiceErrorCode.NOT_FOUND)
        result = self._validate_jsonl_path(str(row.get("path", "")))
        self._save_result(dataset_id, result, approve=False)
        return result

    def approve_dataset(self, dataset_id: str) -> ActionResult:
        row = self.datasets_repo.get_dataset(dataset_id)
        if row is None:
            raise DatasetServiceError(DatasetServiceErrorCode.NOT_FOUND)
        result = self._validate_jsonl_path(str(row.get("path", "")))
        if result.status != DatasetVersionStatus.VALIDATED.value:
            self._save_result(dataset_id, result, approve=False)
            return ActionResult(False, "approval_blocked")
        self._save_result(dataset_id, result, approve=True)
        return ActionResult(True, "approved")

    def compare_dataset_versions(self, dataset_id: str) -> ActionResult:
        if self.datasets_repo.get_dataset(dataset_id) is None:
            return ActionResult(False, "not_found")
        return ActionResult(False, "version_compare_unavailable")

    def preview_dataset(self, dataset_id: str, limit: int = 25) -> tuple[DatasetPreviewRecord, ...]:
        row = self.datasets_repo.get_dataset(dataset_id)
        if row is None:
            return ()
        return self._preview_jsonl_path(str(row.get("path", "")), limit=limit)

    def _save_result(self, dataset_id: str, result: DatasetValidationResult, *, approve: bool) -> None:
        status = (
            DatasetVersionStatus.APPROVED.value
            if approve and result.status == DatasetVersionStatus.VALIDATED.value
            else result.status
        )
        self.datasets_repo.update_dataset_validation(
            dataset_id,
            {
                "status": status,
                "record_count": result.total_rows,
                "valid_count": result.valid_rows,
                "invalid_count": result.invalid_rows,
                "quality_summary": "",
                "validation_errors_preview": "\n".join(
                    encode_dataset_diagnostic(item)
                    for item in result.errors_preview
                ),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _validate_jsonl_path(self, file_path: str) -> DatasetValidationResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return DatasetValidationResult(
                DatasetVersionStatus.VALIDATION_FAILED.value,
                0,
                0,
                0,
                0,
                (dataset_diagnostic("file_not_found"),),
            )
        if path.suffix.lower() != ".jsonl":
            return DatasetValidationResult(
                DatasetVersionStatus.STRUCTURE_ERROR.value,
                0,
                0,
                1,
                0,
                (dataset_diagnostic("only_jsonl"),),
            )

        total_rows = 0
        valid_rows = 0
        invalid_rows = 0
        errors: list[DatasetDiagnostic] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line:
                    continue
                total_rows += 1
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    invalid_rows += 1
                    if len(errors) < 8:
                        errors.append(
                            dataset_diagnostic("invalid_json", line=line_number)
                        )
                    continue
                ok, diagnostic = self._validate_record(payload)
                if ok:
                    valid_rows += 1
                else:
                    invalid_rows += 1
                    if diagnostic is not None and len(errors) < 8:
                        errors.append(
                            DatasetDiagnostic(
                                diagnostic.code,
                                line_number,
                                diagnostic.values,
                            )
                        )

        if total_rows == 0:
            status = DatasetVersionStatus.STRUCTURE_ERROR.value
            errors.append(dataset_diagnostic("empty_file"))
        elif invalid_rows > 0:
            status = DatasetVersionStatus.STRUCTURE_ERROR.value
        else:
            status = DatasetVersionStatus.VALIDATED.value
        return DatasetValidationResult(status, total_rows, valid_rows, invalid_rows, 0, tuple(errors[:8]))

    def _validate_record(
        self,
        payload: object,
    ) -> tuple[bool, DatasetDiagnostic | None]:
        if not isinstance(payload, dict):
            return False, dataset_diagnostic("record_not_object")
        if "messages" in payload:
            messages = payload.get("messages")
            if not isinstance(messages, list) or not messages:
                return False, dataset_diagnostic("messages_not_list")
            has_user = False
            has_assistant = False
            for item in messages:
                if not isinstance(item, dict):
                    return False, dataset_diagnostic("message_not_object")
                role = item.get("role")
                content = item.get("content")
                if role not in {"system", "user", "assistant"}:
                    return False, dataset_diagnostic(
                        "invalid_role",
                        role=str(role),
                    )
                if not isinstance(content, str) or not content.strip():
                    return False, dataset_diagnostic(
                        "content_empty",
                        role=str(role),
                    )
                has_user = has_user or role == "user"
                has_assistant = has_assistant or role == "assistant"
            if not has_user or not has_assistant:
                return False, dataset_diagnostic("messages_missing_pair")
            return True, None
        if "instruction" in payload or "output" in payload:
            instruction = payload.get("instruction")
            output = payload.get("output")
            if not isinstance(instruction, str) or not instruction.strip():
                return False, dataset_diagnostic("instruction_empty")
            if not isinstance(output, str) or not output.strip():
                return False, dataset_diagnostic("output_empty")
            input_field = payload.get("input", "")
            if not isinstance(input_field, str):
                return False, dataset_diagnostic("input_not_string")
            return True, None
        if "prompt" in payload or "response" in payload:
            prompt = payload.get("prompt")
            response = payload.get("response")
            if not isinstance(prompt, str) or not prompt.strip():
                return False, dataset_diagnostic("prompt_empty")
            if not isinstance(response, str) or not response.strip():
                return False, dataset_diagnostic("response_empty")
            return True, None
        return False, dataset_diagnostic("unsupported_schema")

    def _preview_jsonl_path(self, file_path: str, limit: int) -> tuple[DatasetPreviewRecord, ...]:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return (
                DatasetPreviewRecord(
                    "—",
                    dataset_diagnostic("file_not_found"),
                    "—",
                    "structure_error",
                ),
            )
        rows: list[DatasetPreviewRecord] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, start=1):
                if len(rows) >= limit:
                    break
                line = raw.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    rows.append(
                        DatasetPreviewRecord(
                            f"#{line_number:03d}",
                            dataset_diagnostic("invalid_json", line=line_number),
                            "—",
                            "structure_error",
                        )
                    )
                    continue
                ok, diagnostic = self._validate_record(payload)
                if not ok:
                    rows.append(
                        DatasetPreviewRecord(
                            f"#{line_number:03d}",
                            DatasetDiagnostic(
                                diagnostic.code,
                                line_number,
                                diagnostic.values,
                            )
                            if diagnostic is not None
                            else dataset_diagnostic("unknown", line=line_number),
                            "—",
                            "structure_error",
                        )
                    )
                    continue
                rows.append(self._preview_record(line_number, payload))
        return (
            tuple(rows)
            if rows
            else (
                DatasetPreviewRecord(
                    "—",
                    dataset_diagnostic("empty_file"),
                    "—",
                    "structure_error",
                ),
            )
        )

    def _preview_record(self, line_number: int, payload: dict[str, object]) -> DatasetPreviewRecord:
        if "messages" in payload:
            messages = payload.get("messages") or []
            user_text = ""
            assistant_text = ""
            if isinstance(messages, list):
                for item in messages:
                    if not isinstance(item, dict):
                        continue
                    role = item.get("role")
                    content = str(item.get("content", "")).strip()
                    if role == "user" and not user_text:
                        user_text = content
                    if role == "assistant":
                        assistant_text = content
            return DatasetPreviewRecord(f"#{line_number:03d}", self._short(user_text or assistant_text), "messages", "structure_ok")
        if "instruction" in payload or "output" in payload:
            instruction = str(payload.get("instruction", "")).strip()
            input_text = str(payload.get("input", "")).strip()
            summary = instruction if not input_text else f"{instruction} · {input_text}"
            return DatasetPreviewRecord(f"#{line_number:03d}", self._short(summary), "instruction/output", "structure_ok")
        prompt = str(payload.get("prompt", "")).strip()
        return DatasetPreviewRecord(f"#{line_number:03d}", self._short(prompt), "prompt/response", "structure_ok")

    def _short(self, value: str, limit: int = 140) -> str:
        compact = " ".join(value.split())
        return compact if len(compact) <= limit else compact[: limit - 1] + "…"

    def _row_to_summary(self, row: dict[str, str | int]) -> DatasetSummary:
        return DatasetSummary(
            dataset_id=str(row.get("dataset_id", "")),
            title=str(row.get("title", "")),
            subtitle=str(row.get("subtitle", "")),
            status=str(row.get("status", "")),
            record_count=int(row.get("record_count", 0)),
            valid_count=int(row.get("valid_count", 0)),
            invalid_count=int(row.get("invalid_count", 0)),
            quality_summary=str(row.get("quality_summary", "")),
            validation_errors_preview=str(row.get("validation_errors_preview", "")),
            path=str(row.get("path", "")),
            format=str(row.get("format", "jsonl")),
        )
