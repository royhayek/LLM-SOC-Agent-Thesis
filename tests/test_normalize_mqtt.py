"""Tests for the MQTT normalizer (E3-02, SCRUM-27).

Run on fixture logs derived from the real capture format. The count invariant (alerts + skipped ==
lines) is the guard against silent dropping that would bias H1 (§6.9).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from thesis.normalize.mqtt import device_from_client, device_from_topic, normalize_mqtt
from thesis.normalize.store import read_alerts

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "raw"


def _run_dir(tmp_path: Path) -> Path:
    mqtt = tmp_path / "run" / "mqtt"
    mqtt.mkdir(parents=True)
    shutil.copy(FIXTURES / "mqtt_sample.log", mqtt / "mqtt.log")
    shutil.copy(FIXTURES / "mqtt_broker_sample.log", mqtt / "broker.log")
    return tmp_path / "run"


def test_every_line_is_an_alert_or_a_counted_skip(tmp_path: Path) -> None:
    result = normalize_mqtt(_run_dir(tmp_path), "r1", alerts_dir=tmp_path / "alerts")
    # 6 publish lines + 5 broker lines, none blank.
    assert result.lines == 11
    assert result.alerts + result.skipped == 11
    assert result.alerts == 6  # 3 publishes + connect + auth_failure + disconnect
    assert result.skipped == 5


def test_malformed_line_is_skipped_counted_and_logged(tmp_path: Path) -> None:
    result = normalize_mqtt(_run_dir(tmp_path), "r1", alerts_dir=tmp_path / "alerts")
    assert result.skip_reasons["bad_timestamp"] >= 1
    assert result.skip_reasons["unknown_subject"] >= 1
    assert result.skip_log_path is not None
    logged = [json.loads(ln) for ln in result.skip_log_path.read_text().splitlines()]
    assert any("reason" in e and "line" in e for e in logged)


def test_publish_subject_is_the_device_not_the_broker(tmp_path: Path) -> None:
    result = normalize_mqtt(_run_dir(tmp_path), "r1", alerts_dir=tmp_path / "alerts")
    assert result.parquet_path is not None
    alerts = read_alerts(result.parquet_path)
    publishes = [a for a in alerts if getattr(a.detail, "event", None) == "publish"]
    assert publishes and all(a.subject_device.startswith("iot-") for a in publishes)
    assert {a.subject_device for a in publishes} == {"iot-temp-01", "iot-cam-01"}


def test_broker_auth_failure_keys_to_the_device(tmp_path: Path) -> None:
    result = normalize_mqtt(_run_dir(tmp_path), "r1", alerts_dir=tmp_path / "alerts")
    assert result.parquet_path is not None
    alerts = read_alerts(result.parquet_path)
    auth = [a for a in alerts if getattr(a.detail, "event", None) == "auth_failure"]
    assert auth and auth[0].subject_device == "iot-temp-01"


def test_parquet_is_written_at_the_run_path(tmp_path: Path) -> None:
    result = normalize_mqtt(_run_dir(tmp_path), "run-xyz", alerts_dir=tmp_path / "alerts")
    assert result.parquet_path == tmp_path / "alerts" / "mqtt" / "run-xyz.parquet"
    assert result.parquet_path.is_file()


def test_device_mapping_helpers() -> None:
    assert device_from_topic("iot/iot-temp-01/flood") == "iot-temp-01"
    assert device_from_topic("sensors/x/telemetry") is None
    assert device_from_topic("iot/iot-temp-01") is None  # no channel segment
    assert device_from_client("iot-cam-01-brute") == "iot-cam-01"
    assert device_from_client("iot-hum-01-t3") == "iot-hum-01"
    assert device_from_client("mqtt-logger") is None
