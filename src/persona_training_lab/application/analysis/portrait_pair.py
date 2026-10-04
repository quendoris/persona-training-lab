from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.experiments.portrait import (
    PortraitRunRecord,
    parse_portrait_payload,
)
from persona_training_lab.application.experiments.protocol import (
    portrait_protocol_key,
)


@dataclass(frozen=True, slots=True)
class PortraitComparison:
    comparable: bool
    reason_code: str
    left: PortraitRunRecord
    right: PortraitRunRecord
    protocol_key: tuple[str, str] | None
    deltas: Mapping[str, float]

    @property
    def complete(self) -> bool:
        return (
            self.left.total > 0
            and self.left.passed == self.left.total
            and self.right.total > 0
            and self.right.passed == self.right.total
        )


def compare_portrait_payloads(
    left_payload: str,
    right_payload: str,
) -> PortraitComparison:
    left = parse_portrait_payload(left_payload)
    right = parse_portrait_payload(right_payload)
    left_protocol = portrait_protocol_key(left_payload)
    right_protocol = portrait_protocol_key(right_payload)

    if left_protocol is None or right_protocol is None:
        return PortraitComparison(
            comparable=False,
            reason_code="protocol_unknown",
            left=left,
            right=right,
            protocol_key=None,
            deltas=MappingProxyType({}),
        )
    if left_protocol != right_protocol:
        return PortraitComparison(
            comparable=False,
            reason_code="protocol_mismatch",
            left=left,
            right=right,
            protocol_key=None,
            deltas=MappingProxyType({}),
        )

    left_scores = left.trait_scores()
    right_scores = right.trait_scores()
    common = sorted(set(left_scores) & set(right_scores))
    if not common:
        return PortraitComparison(
            comparable=False,
            reason_code="no_common_traits",
            left=left,
            right=right,
            protocol_key=left_protocol,
            deltas=MappingProxyType({}),
        )

    deltas = {
        trait: round(right_scores[trait] - left_scores[trait], 2)
        for trait in common
    }
    return PortraitComparison(
        comparable=True,
        reason_code="comparable",
        left=left,
        right=right,
        protocol_key=left_protocol,
        deltas=MappingProxyType(deltas),
    )


__all__ = ("PortraitComparison", "compare_portrait_payloads")
