from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from persona_training_lab.application.ports.repositories import (
    DatasetsReadRepositoryPort,
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
    errors_preview: tuple[str, ...]


@dataclass(slots=True)
class DatasetsService:
    datasets_repo: DatasetsReadRepositoryPort

    def list_datasets(self) -> list[DatasetSummary]:
        rows = self.datasets_repo.list_datasets()
        return [
            DatasetSummary(
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
            for row in rows
        ]

    def add_dataset_from_path(self, file_path: str) -> DatasetSummary:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise ValueError("Файл датасета не найден")
        if path.suffix.lower() != ".jsonl":
            raise ValueError("Поддерживается только формат .jsonl")

        now = datetime.now(timezone.utc).isoformat()
        dataset_id = f"ds_{uuid4().hex[:8]}"
        payload: dict[str, str | int] = {
            "id": dataset_id,
            "title": path.stem,
            "subtitle": "Локальный JSONL датасет",
            "path": str(path),
            "format": "jsonl",
            "status": "Не проверен",
            "record_count": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "quality_summary": "Не проверен",
            "validation_errors_preview": "",
            "linked_profile": "—",
            "readiness": "Ожидает проверку",
            "schema_name": "jsonl_finetune_v1",
            "created_at": now,
            "updated_at": now,
        }
        self.datasets_repo.add_dataset(payload)

        created = self.datasets_repo.get_dataset(dataset_id)
        if created is None:
            raise RuntimeError("Не удалось сохранить датасет")
        return self._row_to_summary(created)

    def validate_dataset(self, dataset_id: str) -> DatasetValidationResult:
        row = self.datasets_repo.get_dataset(dataset_id)
        if row is None:
            raise ValueError("Датасет не найден")

        path = str(row.get("path", ""))
        result = self._validate_jsonl_path(path)
        now = datetime.now(timezone.utc).isoformat()
        summary = f"Записей: {result.total_rows} · Валидных: {result.valid_rows} · Ошибок: {result.invalid_rows}"
        self.datasets_repo.update_dataset_validation(
            dataset_id,
            {
                "status": result.status,
                "record_count": result.total_rows,
                "valid_count": result.valid_rows,
                "invalid_count": result.invalid_rows,
                "quality_summary": summary,
                "validation_errors_preview": "\n".join(result.errors_preview),
                "updated_at": now,
            },
        )
        return result

    def _validate_jsonl_path(self, file_path: str) -> DatasetValidationResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return DatasetValidationResult(
                status="Не удалось проверить датасет",
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                warning_count=0,
                errors_preview=("строка 0: файл датасета не найден",),
            )
        if path.suffix.lower() != ".jsonl":
            return DatasetValidationResult(
                status="Ошибка структуры",
                total_rows=0,
                valid_rows=0,
                invalid_rows=1,
                warning_count=0,
                errors_preview=("строка 0: поддерживается только формат .jsonl",),
            )

        total_rows = 0
        valid_rows = 0
        invalid_rows = 0
        warning_count = 0
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
                    if len(errors) < 5:
                        errors.append(f"строка {line_number}: невалидный JSON")
                    continue

                ok, message = self._validate_record(payload)
                if ok:
                    valid_rows += 1
                else:
                    invalid_rows += 1
                    if len(errors) < 5:
                        errors.append(f"строка {line_number}: {message}")

        if valid_rows == 0:
            status = "Ошибка структуры"
            if total_rows == 0 and len(errors) < 5:
                errors.append("строка 0: файл не содержит валидных записей")
        elif invalid_rows > 0:
            status = "Есть предупреждения"
        else:
            status = "Готов к обучению"

        return DatasetValidationResult(
            status=status,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            warning_count=warning_count,
            errors_preview=tuple(errors[:5]),
        )

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
                if not isinstance(role, str) or not role.strip():
                    return False, "role должен быть непустой строкой"
                if not isinstance(content, str) or not content.strip():
                    return False, "content должен быть непустой строкой"
                if role == "user":
                    has_user = True
                if role == "assistant":
                    has_assistant = True
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

        return False, "неподдерживаемая схема записи"

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
