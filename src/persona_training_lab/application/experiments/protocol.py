from __future__ import annotations

from persona_training_lab.application.experiments.portrait import (
    parse_portrait_payload,
)


def portrait_protocol_key(payload: str) -> tuple[str, str] | None:
    """Return the comparable portrait protocol identity encoded in a payload."""

    record = parse_portrait_payload(payload)
    battery = record.battery_version.strip()
    scoring = record.scoring_version.strip()
    if not battery or battery == "—" or not scoring or scoring == "—":
        return None
    return battery, scoring


def portrait_protocols_match(left_payload: str, right_payload: str) -> bool:
    """Require both protocol identities to be known and exactly equal."""

    left = portrait_protocol_key(left_payload)
    right = portrait_protocol_key(right_payload)
    return left is not None and right is not None and left == right


__all__ = ("portrait_protocol_key", "portrait_protocols_match")
