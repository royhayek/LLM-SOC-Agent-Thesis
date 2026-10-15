"""Tests for detector annotation (E4-06, SCRUM-68)."""

from __future__ import annotations

from datetime import UTC, datetime

from thesis.detect import annotate
from thesis.detect.annotate import annotate_honeypot, annotate_mqtt, completeness_check
from thesis.schema.alert import Alert, HoneypotDetail, MqttDetail

THRESHOLDS = {
    "benign_channels": ["telemetry"],
    "payload_bytes_p99": 200.0,
    "payload_percentile": 99,
    "auth_failure_score": 0.4,
    "decision_threshold": 0.5,
}


def _mqtt(aid: str) -> Alert:
    return Alert(
        alert_id=aid,
        source="mqtt",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        subject_device="iot-temp-01",
        detail=MqttDetail(event="publish", topic="iot/iot-temp-01/flood", payload_bytes=10),
    )


def _hp(aid: str) -> Alert:
    return Alert(
        alert_id=aid,
        source="honeypot",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        subject_device="hp-ssh-01",
        detail=HoneypotDetail(event="login_success", session_id="s", src_ip="10.77.0.30"),
    )


def test_mqtt_annotation_sets_all_detector_fields() -> None:
    (a,) = annotate_mqtt([_mqtt("m1")], THRESHOLDS)
    assert a.detector_name == "mqtt_thresholds"
    assert a.detector_score == 1.0 and a.detector_label == "novel_topic"


def test_honeypot_annotation_sets_all_detector_fields() -> None:
    (a,) = annotate_honeypot([_hp("h1")])
    assert a.detector_name == "honeypot_rules" and a.detector_label == "login_success"
    assert a.detector_score is not None


def test_completeness_check_flags_unannotated() -> None:
    assert completeness_check([_mqtt("raw")]) == ["raw"]  # not yet annotated
    assert completeness_check(annotate_mqtt([_mqtt("ok")], THRESHOLDS)) == []


def test_flow_annotation_when_model_present() -> None:
    import pytest

    if not annotate.MODEL_PATH.exists():
        pytest.skip("flow model not on disk")
    import json

    import lightgbm as lgb

    from thesis.schema.alert import FlowDetail

    classes = json.loads(annotate.META_PATH.read_text())["classes"]
    booster = lgb.Booster(model_file=str(annotate.MODEL_PATH))
    flow = Alert(
        alert_id="f1",
        source="flows",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        subject_device="iot-cam-01",
        detail=FlowDetail(
            flow_start=datetime(2026, 1, 1, tzinfo=UTC),
            duration_s=1.0,
            src_ip="a",
            src_port=1,
            dst_ip="b",
            dst_port=80,
            protocol="tcp",
            packets_fwd=100,
            packets_bwd=0,
            bytes_fwd=6000,
            bytes_bwd=0,
            syn_count_fwd=100,
            ack_count_fwd=0,
        ),
    )
    (a,) = annotate.annotate_flows([flow], booster, classes)
    assert a.detector_name == "flow_classifier" and a.detector_label in classes
    assert 0.0 <= a.detector_score <= 1.0  # type: ignore[operator]
