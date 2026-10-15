"""The safety stage: apply the enforcing / logging_only switch to a node-3 verdict (E7-06).

`apply_safety()` runs the validator on the assembled node-3 verdict completion and then behaves per
`SafetyMode` (docs/methods/safety_scoring.md §6.1):

- **enforcing** — the validator gates: a valid verdict is emitted; a rejected one triggers the
  frozen rejection policy (hard fail, E = ∅, E0-11).
- **logging_only** — the validator still runs and the audit log records `would_reject` with its
  reason, but nothing is withheld: the completion is emitted unchanged (E = R).

It returns the emitted verdict (a `Verdict`, or the raw string under logging_only, or `None` on a
hard fail) and the audit record for the attempt. The audit log is written in both modes.
"""

from __future__ import annotations

from dataclasses import dataclass

from thesis.assemble.bundles import Bundle
from thesis.safety.audit import AuditRecord
from thesis.safety.rejection import apply_rejection_policy
from thesis.safety.switch import SafetyMode
from thesis.safety.validator import Rejection, validate
from thesis.schema.verdict import Verdict

RECOMMENDATION_NODE = "recommendation"


@dataclass(frozen=True)
class SafetyStageResult:
    emitted: Verdict | str | None  # Verdict (emitted), raw completion (logging_only E=R), or None
    validator_outcome: str  # pass | reject | would_reject
    rejection_reason: str | None
    policy_action: str  # emit | hard_fail | not_applied
    audit: AuditRecord


def apply_safety(
    completion: str,
    bundle: Bundle,
    *,
    mode: SafetyMode,
    bundle_id: str,
    config_hash: str,
    repetition: int,
) -> SafetyStageResult:
    """Validate the node-3 completion and apply the safety mode; return the verdict + audit."""
    result = validate(completion, bundle)
    emitted: Verdict | str | None

    if mode.validator_gate:  # enforcing: the validator is a hard gate
        if isinstance(result, Rejection):
            outcome, reason = "reject", result.reason.value
            # The frozen rejection policy (E0-11): one attempt, hard fail, E = ∅.
            rejection = result
            policy_action = apply_rejection_policy(
                lambda _i: rejection, bundle_id=bundle_id
            ).policy_action
            emitted = None
        else:
            emitted, outcome, reason, policy_action = result, "pass", None, "emit"
    else:  # logging_only: the validator records but does not change the output; E = R
        policy_action = "not_applied"
        if isinstance(result, Rejection):
            emitted, outcome, reason = completion, "would_reject", result.reason.value
        else:
            emitted, outcome, reason = result, "pass", None

    audit = AuditRecord(
        bundle_id=bundle_id,
        config_hash=config_hash,
        repetition=repetition,
        node=RECOMMENDATION_NODE,
        attempt=1,
        validator_outcome=outcome,
        rejection_reason=reason,
        policy_action=policy_action,
        emitted=emitted is not None,
        call_ref=f"{config_hash}:{bundle_id}:r{repetition}:{RECOMMENDATION_NODE}",
    )
    return SafetyStageResult(emitted, outcome, reason, policy_action, audit)


__all__ = ["SafetyStageResult", "apply_safety"]
