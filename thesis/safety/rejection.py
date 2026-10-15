"""The frozen rejection policy (E7-04, SCRUM-66).

What happens after the validator (E7-02) rejects node 3's completion changes the measured unsafe
rate, so the policy was frozen in E0-11 before any result (`rejection-policy-v1.0`,
docs/methods/rejection_policy.md). This applies exactly that policy under `enforcing`:

- **hard fail**: a rejected completion emits nothing — `E = ∅` — with no substitute verdict;
- **max_retries = 0**: the recommendation call is never repeated (a retry would break the
  three-call and no-history rules and need a retry prompt — §7);
- one scored attempt per bundle+repetition, so first and final attempt are the same completion.

Parameters are read from `config/rejection_policy.yaml`, never hard-coded (AC). Every attempt is
logged with its index; the audit-log *format* is E7-05, and the `logging_only` path is E7-06.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import structlog
import yaml  # type: ignore[import-untyped]

from thesis.safety.validator import Rejection
from thesis.schema.verdict import Verdict

PARAMS_PATH = Path(__file__).resolve().parents[2] / "config" / "rejection_policy.yaml"

_log = structlog.get_logger("thesis.safety.rejection")


@dataclass(frozen=True)
class PolicyParams:
    policy: str
    max_retries: int
    scored_attempt: str

    @classmethod
    def load(cls, path: Path = PARAMS_PATH) -> PolicyParams:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(
            policy=str(data["policy"]),
            max_retries=int(data["max_retries"]),
            scored_attempt=str(data["scored_attempt"]),
        )


@dataclass(frozen=True)
class AttemptRecord:
    attempt: int
    validator_outcome: str  # "pass" or "reject"
    rejection_reason: str | None


@dataclass(frozen=True)
class PolicyOutcome:
    """The result of applying the policy: what is emitted (E) and the per-attempt record."""

    emitted: Verdict | None  # the emitted verdict E, or None on hard fail (E = ∅)
    policy_action: str  # "emit" or "hard_fail"
    attempts: list[AttemptRecord]
    final_rejection: Rejection | None

    @property
    def first_attempt(self) -> AttemptRecord:
        return self.attempts[0]

    @property
    def final_attempt(self) -> AttemptRecord:
        return self.attempts[-1]


def apply_rejection_policy(
    attempt_fn: Callable[[int], Verdict | Rejection],
    *,
    bundle_id: str,
    params: PolicyParams | None = None,
) -> PolicyOutcome:
    """Run the recommendation attempt(s) under the frozen policy and return the outcome.

    `attempt_fn(i)` runs node 3's call for attempt `i` and validates it, returning a `Verdict` on
    pass or a `Rejection`. It is never given a previous completion, so no conversation accumulates.
    """
    params = params or PolicyParams.load()
    attempts: list[AttemptRecord] = []
    last_rejection: Rejection | None = None

    for attempt in range(1, params.max_retries + 2):  # 1 initial call + max_retries retries
        result = attempt_fn(attempt)
        if isinstance(result, Verdict):
            attempts.append(AttemptRecord(attempt, "pass", None))
            _log.info(
                "rejection_policy",
                bundle_id=bundle_id,
                attempt=attempt,
                outcome="pass",
                policy_action="emit",
            )
            return PolicyOutcome(result, "emit", attempts, None)
        last_rejection = result
        attempts.append(AttemptRecord(attempt, "reject", result.reason.value))
        _log.info(
            "rejection_policy",
            bundle_id=bundle_id,
            attempt=attempt,
            outcome="reject",
            rejection_reason=result.reason.value,
            policy_action="hard_fail",
        )

    return PolicyOutcome(None, "hard_fail", attempts, last_rejection)


__all__ = ["AttemptRecord", "PolicyOutcome", "PolicyParams", "apply_rejection_policy"]
