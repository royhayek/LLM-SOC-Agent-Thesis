"""Tests for the deterministic validator (E7-02, SCRUM-43): one per rejection reason, plus valid."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from thesis.assemble.bundles import Bundle
from thesis.safety.validator import Rejection, RejectionReason, validate
from thesis.schema.alert import Alert, FlowDetail
from thesis.schema.verdict import Verdict

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _bundle() -> Bundle:
    alert = Alert(
        alert_id="f1",
        source="flows",
        ts=T0,
        subject_device="iot-cam-01",
        detector_score=0.9,
        detector_label="syn_flood",
        detector_name="flow_classifier",
        detail=FlowDetail(
            flow_start=T0,
            duration_s=1.0,
            src_ip="10.77.0.22",
            src_port=5,
            dst_ip="192.0.2.1",
            dst_port=80,
            protocol="tcp",
            packets_fwd=10,
            packets_bwd=0,
            bytes_fwd=600,
            bytes_bwd=0,
        ),
    )
    return Bundle(
        bundle_id="iot-cam-01|w",
        device="iot-cam-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="syn_flood",
        episode_id="ep-1",
        sources=("flows",),
        alerts=(alert,),
    )


def _verdict(action: str = "rate_limit_source", evidence: list[str] | None = None) -> str:
    return json.dumps(
        {
            "classification": {"incident_type": "syn_flood", "confidence": 0.8},
            "recommendation": {"recommended_action": action, "severity": "high"},
            "affected_device": "iot-cam-01",
            "evidence": evidence if evidence is not None else ["f1"],
        }
    )


def test_not_json_is_malformed() -> None:
    result = validate("this is not json", _bundle())
    assert result == Rejection(RejectionReason.MALFORMED)


def test_json_that_is_not_a_verdict_is_malformed() -> None:
    # Valid JSON, a catalog action, but the rest of the schema is missing.
    bad = json.dumps({"recommendation": {"recommended_action": "monitor"}})
    assert validate(bad, _bundle()) == Rejection(RejectionReason.MALFORMED)


def test_action_outside_the_catalog_is_action_out_of_space() -> None:
    result = validate(_verdict(action="launch_counterattack"), _bundle())
    assert result == Rejection(RejectionReason.ACTION_OUT_OF_SPACE)


def test_unknown_evidence_is_rejected_with_the_offending_ids() -> None:
    result = validate(_verdict(evidence=["f1", "ghost-7"]), _bundle())
    assert isinstance(result, Rejection)
    assert result.reason is RejectionReason.UNKNOWN_EVIDENCE
    assert result.detail == ["ghost-7"]


def test_valid_completion_returns_the_verdict() -> None:
    result = validate(_verdict(), _bundle())
    assert isinstance(result, Verdict)
    assert result.recommendation.recommended_action.value == "rate_limit_source"
    assert result.evidence == ["f1"]
