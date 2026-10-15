"""The deterministic validator: the hard gate between the model and any human (E7-02, SCRUM-43).

`validate()` is a pure function (no network, no LLM). It turns a raw completion into either a valid
`Verdict` or a typed `Rejection` with exactly one of three reasons (record §3.3, §6.4):

- `malformed` — not valid JSON, or valid JSON that does not fit the `Verdict` schema;
- `action_out_of_space` — a recommended action that is not a catalog id;
- `unknown_evidence` — an evidence id that is not an alert in this bundle.

Hallucinated evidence would destroy auditability, the project's differentiator, so unknown
evidence is a hard rejection. The validator **never repairs** a near-miss output: repairing would
turn the gate into a filter and change what H3 measures (the gotcha). What happens after a
rejection is E7-04; contextual-safety scoring is E9-04.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import ValidationError

from thesis.assemble.bundles import Bundle
from thesis.schema.verdict import ACTION_IDS, Verdict


class RejectionReason(StrEnum):
    MALFORMED = "malformed"
    ACTION_OUT_OF_SPACE = "action_out_of_space"
    UNKNOWN_EVIDENCE = "unknown_evidence"


@dataclass(frozen=True)
class Rejection:
    """A rejected completion, with its single reason and (where useful) the offending detail."""

    reason: RejectionReason
    detail: list[str] = field(default_factory=list)


def _recommended_action(data: dict[str, object]) -> object:
    recommendation = data.get("recommendation")
    return recommendation.get("recommended_action") if isinstance(recommendation, dict) else None


def validate(completion: str, bundle: Bundle) -> Verdict | Rejection:
    """Return a valid `Verdict` or a `Rejection`. Never repairs; exactly one reason on rejection."""
    try:
        data = json.loads(completion)
    except (json.JSONDecodeError, ValueError):
        return Rejection(RejectionReason.MALFORMED)
    if not isinstance(data, dict):
        return Rejection(RejectionReason.MALFORMED)

    # The action check runs before the full schema parse, so an out-of-catalog action is reported
    # as `action_out_of_space`, not lumped into `malformed`.
    if _recommended_action(data) not in ACTION_IDS:
        return Rejection(RejectionReason.ACTION_OUT_OF_SPACE)

    try:
        verdict = Verdict.model_validate(data)
    except ValidationError:
        return Rejection(RejectionReason.MALFORMED)

    valid_ids = {alert.alert_id for alert in bundle.alerts}
    unknown = [e for e in verdict.evidence if e not in valid_ids]
    if unknown:
        return Rejection(RejectionReason.UNKNOWN_EVIDENCE, detail=unknown)

    return verdict


__all__ = ["Rejection", "RejectionReason", "validate"]
