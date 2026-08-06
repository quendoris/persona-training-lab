from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping
import re

from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
    normalize_local_model_status,
)


CASE_HEADER_RE = re.compile(r"(?m)^CASE\s+(\d+)\s*$")
SCORE_RE = re.compile(r"\bSCORE\s*:\s*([1-5])\b", re.IGNORECASE)
SUMMARY_RE = re.compile(
    r"^(?:PORTRAIT|SUMMARY)\s*:\s*(\d+)\s*/\s*(\d+)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PortraitCaseRecord:
    index: int
    fields: Mapping[str, str]
    raw_block: str

    def field(self, name: str) -> str:
        return self.fields.get(name.upper(), "")

    @property
    def trait(self) -> str:
        return self.field("TRAIT") or self.field("DIMENSION")

    @property
    def key(self) -> str:
        return self.field("KEY")

    @property
    def reverse(self) -> bool:
        return self.field("REVERSE") == "1"

    @property
    def item(self) -> str:
        return (
            self.field("ITEM")
            or self.field("QUESTION")
            or self.field("PROMPT")
        )

    @property
    def raw_status(self) -> str:
        return self.field("STATUS")

    @property
    def status_code(self) -> LocalModelStatus:
        return normalize_local_model_status(self.raw_status)

    @property
    def response(self) -> str:
        return self.field("RESPONSE")

    @property
    def raw_response(self) -> str:
        return self.field("RAW_RESPONSE")

    @property
    def valid_score(self) -> bool:
        marker = self.field("VALID_SCORE")
        if marker:
            return marker == "1"
        return self.score is not None

    @property
    def score(self) -> int | None:
        match = SCORE_RE.search(self.response or self.raw_response)
        return int(match.group(1)) if match is not None else None

    @property
    def adjusted_score(self) -> int | None:
        score = self.score
        if score is None:
            return None
        return 6 - score if self.reverse else score


@dataclass(frozen=True, slots=True)
class PortraitRunRecord:
    raw_summary: str
    passed: int
    total: int
    labels: tuple[str, ...]
    metadata: Mapping[str, str] = field(default_factory=dict)
    cases: tuple[PortraitCaseRecord, ...] = ()

    def metadata_value(self, key: str) -> str:
        return self.metadata.get(key.casefold(), "")

    @property
    def model_version_id(self) -> str:
        return self.metadata_value("model_version")

    @property
    def artifact_path(self) -> str:
        return self.metadata_value("artifact")

    @property
    def battery_version(self) -> str:
        return self.metadata_value("battery")

    @property
    def scoring_version(self) -> str:
        return self.metadata_value("scoring")

    @property
    def invalid_count(self) -> int:
        return sum(
            1
            for case in self.cases
            if not case.valid_score
            or case.status_code is not LocalModelStatus.RESPONDING
        )

    @property
    def answer_count(self) -> int:
        return sum(1 for case in self.cases if case.valid_score)

    def trait_scores(self) -> dict[str, float]:
        grouped: dict[str, list[float]] = {}
        for case in self.cases:
            score = case.adjusted_score
            if not case.trait or score is None or not case.valid_score:
                continue
            grouped.setdefault(case.trait, []).append(float(score))
        return {
            trait: round(sum(values) / len(values), 2)
            for trait, values in grouped.items()
            if values
        }


def parse_portrait_payload(payload: str) -> PortraitRunRecord:
    text = str(payload or "")
    header_match = CASE_HEADER_RE.search(text)
    if header_match is None:
        summary = text.strip()
        passed, total = _parse_passed_total(summary)
        labels, metadata = _parse_summary_segments(summary)
        return PortraitRunRecord(
            raw_summary=summary,
            passed=passed,
            total=total,
            labels=labels,
            metadata=MappingProxyType(metadata),
        )

    summary = text[: header_match.start()].strip()
    passed, total = _parse_passed_total(summary)
    labels, metadata = _parse_summary_segments(summary)
    matches = list(CASE_HEADER_RE.finditer(text))
    cases: list[PortraitCaseRecord] = []
    for position, match in enumerate(matches):
        start = match.end()
        end = (
            matches[position + 1].start()
            if position + 1 < len(matches)
            else len(text)
        )
        block = text[start:end].strip()
        fields = _parse_fields(block)
        cases.append(
            PortraitCaseRecord(
                index=int(match.group(1)),
                fields=MappingProxyType(fields),
                raw_block=block,
            )
        )
    return PortraitRunRecord(
        raw_summary=summary,
        passed=passed,
        total=total,
        labels=labels,
        metadata=MappingProxyType(metadata),
        cases=tuple(cases),
    )


def _parse_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        key = name.strip().upper()
        if key and key not in fields:
            fields[key] = value.strip()
    return fields


def _parse_passed_total(summary: str) -> tuple[int, int]:
    first_line = summary.splitlines()[0].strip() if summary else ""
    match = SUMMARY_RE.match(first_line)
    if match is None:
        return 0, 0
    return int(match.group(1)), int(match.group(2))


def _parse_summary_segments(
    summary: str,
) -> tuple[tuple[str, ...], dict[str, str]]:
    first_line = summary.splitlines()[0].strip() if summary else ""
    segments = [segment.strip() for segment in first_line.split(" · ")]
    labels: list[str] = []
    metadata: dict[str, str] = {}
    for segment in segments[1:]:
        if "=" not in segment:
            if segment:
                labels.append(segment)
            continue
        key, value = segment.split("=", 1)
        metadata[key.strip().casefold()] = value.strip()
    return tuple(labels), metadata
