"""Tests for the frozen rejection policy (E7-04, SCRUM-66). The recommendation call is mocked."""

from __future__ import annotations

from thesis.safety.rejection import PolicyParams, apply_rejection_policy
from thesis.safety.validator import Rejection, RejectionReason
from thesis.schema.verdict import Verdict

VERDICT = Verdict.model_validate(
    {
        "classification": {"incident_type": "syn_flood", "confidence": 0.8},
        "recommendation": {"recommended_action": "rate_limit_source", "severity": "high"},
        "affected_device": "iot-cam-01",
        "evidence": ["f1"],
    }
)
REJECT = Rejection(RejectionReason.UNKNOWN_EVIDENCE, detail=["ghost"])


def test_params_come_from_the_frozen_file() -> None:
    params = PolicyParams.load()
    assert params.policy == "hard_fail"
    assert params.max_retries == 0
    assert params.scored_attempt == "single"


def test_valid_first_attempt_emits_and_calls_once() -> None:
    calls = []
    outcome = apply_rejection_policy(lambda i: calls.append(i) or VERDICT, bundle_id="b")
    assert calls == [1]  # frozen max_retries = 0: a single attempt
    assert outcome.policy_action == "emit"
    assert outcome.emitted is VERDICT
    assert outcome.first_attempt is outcome.final_attempt


def test_rejected_first_attempt_hard_fails_without_retry() -> None:
    calls = []
    outcome = apply_rejection_policy(lambda i: calls.append(i) or REJECT, bundle_id="b")
    assert calls == [1]  # no retry after a rejection (max_retries = 0)
    assert outcome.policy_action == "hard_fail"
    assert outcome.emitted is None  # E = ∅, no substitute verdict
    assert outcome.final_rejection == REJECT
    assert outcome.final_attempt.rejection_reason == "unknown_evidence"


def test_retry_loop_respects_a_higher_max_and_stops_at_the_cap() -> None:
    # Not the frozen value; proves the loop honours the parameter rather than a constant.
    params = PolicyParams(policy="hard_fail", max_retries=2, scored_attempt="single")
    calls = []
    outcome = apply_rejection_policy(
        lambda i: calls.append(i) or REJECT, bundle_id="b", params=params
    )
    assert calls == [1, 2, 3]  # 1 initial + 2 retries, all rejected
    assert outcome.policy_action == "hard_fail"


def test_loop_stops_at_the_first_valid_attempt() -> None:
    params = PolicyParams(policy="hard_fail", max_retries=2, scored_attempt="single")
    replies = {1: REJECT, 2: VERDICT}
    calls = []
    outcome = apply_rejection_policy(
        lambda i: calls.append(i) or replies[i], bundle_id="b", params=params
    )
    assert calls == [1, 2]  # stopped as soon as an attempt passed
    assert outcome.policy_action == "emit"
