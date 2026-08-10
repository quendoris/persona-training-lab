from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from persona_training_lab.application.messages import ActionResult
from persona_training_lab.application.ports.repositories import DatasetsReadRepositoryPort


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
    errors_preview: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class DatasetPreviewRecord:
    row_id: str
    input_summary: str
    traits: str
    quality: str


@dataclass(slots=True)
class DatasetsService:
    datasets_repo: DatasetsReadRepositoryPort

    def list_datasets(self) -> list[DatasetSummary]:
        return [self._row_to_summary(row) for row in self.datasets_repo.list_datasets()]

    def add_dataset_from_path(self, file_path: str) -> DatasetSummary:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise ValueError("Файл датасета не найден")
        if path.suffix.lower() != ".jsonl":
            raise ValueError("Поддерживается только формат .jsonl")

        now = datetime.now(timezone.utc).isoformat()
        dataset_id = f"ds_{uuid4().hex[:8]}"
        self.datasets_repo.add_dataset(
            {
                "id": dataset_id,
                "title": path.stem,
                "subtitle": "Локальный JSONL датасет",
                "path": str(path),
                "format": "jsonl",
                "status": "Не проверен",
                "record_count": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "quality_summary": "Автопроверка смотрит только структуру JSONL и обязательные поля. Смысл утверждает автор.",
                "validation_errors_preview": "",
                "linked_profile": "—",
                "readiness": "Ожидает проверку",
                "schema_name": "jsonl_finetune_v1",
                "created_at": now,
                "updated_at": now,
            }
        )
        created = self.datasets_repo.get_dataset(dataset_id)
        if created is None:
            raise RuntimeError("Не удалось сохранить датасет")
        return self._row_to_summary(created)

    def validate_dataset(self, dataset_id: str) -> DatasetValidationResult:
        row = self.datasets_repo.get_dataset(dataset_id)
        if row is None:
            raise ValueError("Датасет не найден")
        result = self._validate_jsonl_path(str(row.get("path", "")))
        self._save_result(dataset_id, result, approve=False)
        return result

    def approve_dataset(self, dataset_id: str) -> ActionResult:
        row = self.datasets_repo.get_dataset(dataset_id)
        if row is None:
            raise ValueError("Датасет не найден")
        result = self._validate_jsonl_path(str(row.get("path", "")))
        if result.status != "Готов к обучению":
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
        status = "Одобрен для обучения" if approve and result.status == "Готов к обучению" else result.status
        now = datetime.now(timezone.utc).isoformat()
        if status == "Одобрен для обучения":
            summary = f"Одобрено автором · структура OK · записей: {result.total_rows} · валидных: {result.valid_rows}."
        elif result.status == "Готов к обучению":
            summary = f"Структура OK · записей: {result.total_rows} · валидных: {result.valid_rows}. Нажмите «Одобрить для обучения»."
        else:
            summary = f"Ошибка структуры · записей: {result.total_rows} · ошибок: {result.invalid_rows}"
        self.datasets_repo.update_dataset_validation(
            dataset_id,
            {
                "status": status,
                "record_count": result.total_rows,
                "valid_count": result.valid_rows,
                "invalid_count": result.invalid_rows,
                "quality_summary": summary,
                "validation_errors_preview": "\n".join(result.errors_preview),
                "updated_at": now,
            },
        )

    def _validate_jsonl_path(self, file_path: str) -> DatasetValidationResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return DatasetValidationResult("Не удалось проверить датасет", 0, 0, 0, 0, ("строка 0: файл датасета не найден",))
        if path.suffix.lower() != ".jsonl":
            return DatasetValidationResult("Ошибка структуры", 0, 0, 1, 0, ("строка 0: поддерживается только формат .jsonl",))

        total_rows = 0
        valid_rows = 0
        invalid_rows = 0
        errors: list[str] = []
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
                        errors.append(f"строка {line_number}: невалидный JSON")
                    continue
                ok, message = self._validate_record(payload)
                if ok:
                    valid_rows += 1
                else:
                    invalid_rows += 1
                    if len(errors) < 8:
                        errors.append(f"строка {line_number}: {message}")

        if total_rows == 0:
            status = "Ошибка структуры"
            errors.append("строка 0: файл не содержит записей")
        elif invalid_rows > 0:
            status = "Ошибка структуры"
        else:
            status = "Готов к обучению"
        return DatasetValidationResult(status, total_rows, valid_rows, invalid_rows, 0, tuple(errors[:8]))

    def _validate_record(self, payload: object) -> tuple[bool, str]:
        if not isinstance(payload, dict):
            return False, "запись должна быть объектом"
        if "messages" in payload:
            messages = payload.get("messages")
            if not isinstance(messages, list) or not messages:
                return False, "поле messages должно быть непустым списком"
            has_user = False
            has_assistant = False
            for item in messages:
                if not isinstance(item, dict):
                    return False, "элементы messages должны быть объектами"
                role = item.get("role")
                content = item.get("content")
                if role not in {"system", "user", "assistant"}:
                    return False, "role должен быть system, user или assistant"
                if not isinstance(content, str) or not content.strip():
                    return False, "content должен быть непустой строкой"
                has_user = has_user or role == "user"
                has_assistant = has_assistant or role == "assistant"
            if not has_user or not has_assistant:
                return False, "messages должен содержать user и assistant"
            return True, "ok"
        if "instruction" in payload or "output" in payload:
            instruction = payload.get("instruction")
            output = payload.get("output")
            if not isinstance(instruction, str) or not instruction.strip():
                return False, "instruction должен быть непустой строкой"
            if not isinstance(output, str) or not output.strip():
                return False, "output должен быть непустой строкой"
            input_field = payload.get("input", "")
            if not isinstance(input_field, str):
                return False, "input должен быть строкой"
            return True, "ok"
        if "prompt" in payload or "response" in payload:
            prompt = payload.get("prompt")
            response = payload.get("response")
            if not isinstance(prompt, str) or not prompt.strip():
                return False, "prompt должен быть непустой строкой"
            if not isinstance(response, str) or not response.strip():
                return False, "response должен быть непустой строкой"
            return True, "ok"
        return False, "поддерживаются схемы messages, instruction/output или prompt/response"

    def _preview_jsonl_path(self, file_path: str, limit: int) -> tuple[DatasetPreviewRecord, ...]:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return (DatasetPreviewRecord("—", "Файл датасета не найден", "—", "ошибка структуры"),)
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
                    rows.append(DatasetPreviewRecord(f"#{line_number:03d}", "Невалидный JSON", "—", "ошибка структуры"))
                    continue
                ok, message = self._validate_record(payload)
                if not ok:
                    rows.append(DatasetPreviewRecord(f"#{line_number:03d}", message, "—", "ошибка структуры"))
                    continue
                rows.append(self._preview_record(line_number, payload))
        return tuple(rows) if rows else (DatasetPreviewRecord("—", "Файл не содержит записей", "—", "ошибка структуры"),)

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
            return DatasetPreviewRecord(f"#{line_number:03d}", self._short(user_text or assistant_text or "messages"), "messages", "структура OK")
        if "instruction" in payload or "output" in payload:
            instruction = str(payload.get("instruction", "")).strip()
            input_text = str(payload.get("input", "")).strip()
            summary = instruction if not input_text else f"{instruction} · input: {input_text}"
            return DatasetPreviewRecord(f"#{line_number:03d}", self._short(summary), "instruction/output", "структура OK")
        prompt = str(payload.get("prompt", "")).strip()
        return DatasetPreviewRecord(f"#{line_number:03d}", self._short(prompt), "prompt/response", "структура OK")

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
