"""Checks on alert schema v0.1 and the device-mapping rule (E0-08)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from thesis.schema.alert import SCHEMA_VERSION, Alert, Source
from thesis.schema.devices import (
    DEVICES,
    HONEYPOT_ID,
    INFRASTRUCTURE,
    subject_device,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "alerts"
BROKER_IP = "172.20.0.2"
IOT_IP = "172.20.0.21"


def fixture_text(source: Source) -> str:
    return (FIXTURES / f"{source}.json").read_text(encoding="utf-8").strip()


@pytest.mark.parametrize("source", list(Source))
def test_example_round_trips_to_identical_json(source: Source) -> None:
    text = fixture_text(source)
    alert = Alert.model_validate_json(text)
    assert alert.source is source
    assert alert.to_json() == text


def test_schema_version() -> None:
    assert SCHEMA_VERSION == "alert-v1"
    assert Alert.model_validate_json(fixture_text(Source.FLOWS)).schema_version == SCHEMA_VERSION


def test_unknown_field_is_rejected() -> None:
    data = json.loads(fixture_text(Source.FLOWS))
    data["detail"]["anomaly_scor"] = 0.9
    with pytest.raises(ValidationError):
        Alert.model_validate(data)


def test_detail_must_match_source() -> None:
    data = json.loads(fixture_text(Source.HONEYPOT))
    data["source"] = "flows"
    with pytest.raises(ValidationError):
        Alert.model_validate(data)


def test_naive_timestamp_is_rejected() -> None:
    data = json.loads(fixture_text(Source.MQTT))
    data["ts"] = "2026-09-14T10:15:12.5"
    with pytest.raises(ValidationError):
        Alert.model_validate(data)


@pytest.mark.parametrize("source", [Source.FLOWS, Source.MQTT])
def test_device_to_broker_maps_to_device(source: Source) -> None:
    assert subject_device(source, IOT_IP, BROKER_IP) == DEVICES[IOT_IP]
    assert subject_device(source, BROKER_IP, IOT_IP) == DEVICES[IOT_IP]


@pytest.mark.parametrize("src_ip", ["203.0.113.45", IOT_IP, BROKER_IP, "10.0.0.99"])
def test_honeypot_event_maps_to_honeypot(src_ip: str) -> None:
    assert subject_device(Source.HONEYPOT, src_ip, None) == HONEYPOT_ID


def test_attacker_flow_to_honeypot_maps_to_honeypot() -> None:
    assert subject_device(Source.FLOWS, "203.0.113.45", "172.20.0.10") == HONEYPOT_ID


def test_infrastructure_only_flow_has_no_subject() -> None:
    assert subject_device(Source.FLOWS, "172.20.0.1", BROKER_IP) is None


def test_external_to_infrastructure_flow_has_no_subject() -> None:
    # Case 4 (E3-10): an external host to an infrastructure host forms no bundle.
    assert subject_device(Source.FLOWS, "203.0.113.45", BROKER_IP) is None


def test_device_to_device_flow_has_no_subject() -> None:
    # Case 5 (E3-10): device-to-device traffic forms no bundle (no longer raises).
    assert subject_device(Source.FLOWS, IOT_IP, "172.20.0.22") is None


def test_infrastructure_list() -> None:
    assert {"gateway", "mqtt-broker", "capture-sidecar"} <= set(INFRASTRUCTURE.values())
    assert set(INFRASTRUCTURE).isdisjoint(DEVICES)
    assert HONEYPOT_ID in DEVICES.values()


def test_mqtt_publish_without_client_or_addresses_is_valid() -> None:
    # v1: a publish seen on the subscriber log has only topic + payload (E3-01).
    alert = Alert.model_validate(
        {
            "alert_id": "mq-9",
            "source": "mqtt",
            "ts": "2026-09-14T10:15:12.500000Z",
            "subject_device": "iot-temp-01",
            "detail": {"event": "publish", "topic": "iot/iot-temp-01/flood", "payload_bytes": 48},
        }
    )
    assert alert.detail.client_id is None  # type: ignore[union-attr]


def test_detector_fields_default_none_and_are_omitted() -> None:
    alert = Alert.model_validate_json(fixture_text(Source.HONEYPOT))
    assert alert.detector_score is None and alert.detector_label is None
    assert "detector_score" not in alert.to_json()  # exclude_none keeps the view cheap


def test_flow_syn_ack_counts_round_trip() -> None:
    alert = Alert.model_validate_json(fixture_text(Source.FLOWS))
    assert alert.detail.syn_count_fwd == 1 and alert.detail.ack_count_fwd == 0  # type: ignore[union-attr]
    assert alert.detector_score == 0.97
