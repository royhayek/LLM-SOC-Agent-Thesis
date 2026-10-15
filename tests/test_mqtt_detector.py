"""Tests for the MQTT threshold detector (E4-04, SCRUM-48)."""

from __future__ import annotations

from datetime import UTC, datetime

from thesis.detect import mqtt as det
from thesis.schema.alert import Alert, MqttDetail

THRESHOLDS = {
    "benign_channels": ["status", "telemetry"],
    "payload_bytes_p99": 200.0,
    "payload_percentile": 99,
    "auth_failure_score": 0.4,
    "decision_threshold": 0.5,
}


def _mqtt(event: str, topic: str | None = None, payload: int | None = None) -> Alert:
    return Alert(
        alert_id="m",
        source="mqtt",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        subject_device="iot-temp-01",
        detail=MqttDetail(event=event, topic=topic, payload_bytes=payload),
    )


def test_score_is_in_range_and_labelled() -> None:
    score, label = det.score_mqtt(_mqtt("publish", "iot/iot-temp-01/telemetry", 50), THRESHOLDS)
    assert 0.0 <= score <= 1.0 and isinstance(label, str)


def test_flood_channel_scores_high() -> None:
    score, label = det.score_mqtt(_mqtt("publish", "iot/iot-temp-01/flood", 10), THRESHOLDS)
    assert score == 1.0 and label == "novel_topic"


def test_benign_publish_scores_zero() -> None:
    assert det.score_mqtt(_mqtt("publish", "iot/iot-temp-01/telemetry", 50), THRESHOLDS) == (
        0.0,
        "benign",
    )


def test_refused_login_stays_below_decision_threshold() -> None:
    score, label = det.score_mqtt(_mqtt("auth_failure"), THRESHOLDS)
    assert label == "auth_failure" and score < THRESHOLDS["decision_threshold"]


def test_large_payload_scores_above_zero() -> None:
    score, label = det.score_mqtt(_mqtt("publish", "iot/iot-temp-01/telemetry", 1000), THRESHOLDS)
    assert score > 0.5 and label == "large_payload"


def test_calibrate_from_benign_alerts() -> None:
    benign = [
        _mqtt("publish", "iot/iot-temp-01/telemetry", 48),
        _mqtt("publish", "iot/iot-cam-01/status", 120),
    ]
    t = det.calibrate(benign)
    assert set(t["benign_channels"]) == {"telemetry", "status"}
    assert t["payload_bytes_p99"] >= 48
