"""Normalize MQTT telemetry into alerts (E3-02, SCRUM-27).

Two logs make the MQTT evidence H1 compares: the subscriber log `mqtt/mqtt.log` (one line per
publish: `<ts> <topic> <payload>`) and the broker log `mqtt/broker.log` (`<ts>: <message>` for
connects, disconnects and refused authentications). Every line becomes one `Alert` or is counted
as skipped with a reason and written to the skip log; the run never stops on a bad line (§6.9).

The MQTT subject device is read from the topic (`iot/<device>/…`) or the client id
(`iot-<name>-NN[-suffix]`), per the alert-schema v1 decision (E3-01): a publish on the subscriber
log carries no IP, so the IP-based `subject_device()` (§4.1) does not apply here. The device id is
taken from the topic/client shape; validating it against the real device inventory is E5-01.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from thesis.normalize.store import ALERTS_DIR, NormalizeResult, write_alerts
from thesis.schema.alert import Alert, MqttDetail, Source

_DEVICE = re.compile(r"^(iot-[a-z]+-\d+)(?:-.*)?$")


def _parse_ts(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # broker.log is naive; treat as UTC


def device_from_topic(topic: str) -> str | None:
    segs = topic.split("/")
    if len(segs) >= 3 and segs[0] == "iot" and _DEVICE.match(segs[1]):
        return segs[1]
    return None


def device_from_client(client_id: str) -> str | None:
    m = _DEVICE.match(client_id)
    return m.group(1) if m else None


def _publish_alert(line: str, alert_id: str) -> tuple[Alert | None, str | None]:
    parts = line.split(" ", 2)
    if len(parts) < 3:
        return None, "malformed"
    ts_raw, topic, payload = parts
    try:
        ts = _parse_ts(ts_raw)
    except ValueError:
        return None, "bad_timestamp"
    device = device_from_topic(topic)
    if device is None:
        return None, "unknown_subject"
    detail = MqttDetail(event="publish", topic=topic, payload_bytes=len(payload.encode("utf-8")))
    return Alert(
        alert_id=alert_id, source=Source.MQTT, ts=ts, subject_device=device, detail=detail
    ), None


def _broker_alert(line: str, alert_id: str) -> tuple[Alert | None, str | None]:
    head, sep, msg = line.partition(": ")
    if not sep:
        return None, "malformed"
    try:
        ts = _parse_ts(head)
    except ValueError:
        return None, "bad_timestamp"

    if msg.startswith("Client ") and msg.rstrip().endswith("not authorised."):
        event, client_id = "auth_failure", msg.split()[1]
    elif msg.startswith("New client connected from ") and " as " in msg:
        event, client_id = "connect", msg.split(" as ", 1)[1].split(" ", 1)[0].rstrip("(")
    elif msg.startswith("Client ") and ("disconnected" in msg or "closed its connection" in msg):
        event, client_id = "disconnect", msg.split()[1]
    else:
        return None, "not_client_event"  # broker lifecycle / connection preamble

    device = device_from_client(client_id)
    if device is None:
        return None, "unknown_subject"  # e.g. the mqtt-logger subscriber, not a device
    detail = MqttDetail(event=event, client_id=client_id)
    return Alert(
        alert_id=alert_id, source=Source.MQTT, ts=ts, subject_device=device, detail=detail
    ), None


_Parser = Callable[[str, str], tuple[Alert | None, str | None]]


def _process(
    lines: list[str], parse: _Parser, prefix: str, start: int, result: NormalizeResult
) -> tuple[list[Alert], list[dict[str, object]]]:
    alerts: list[Alert] = []
    skips: list[dict[str, object]] = []
    seq = start
    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")
        if not line.strip():
            continue  # blank lines are not telemetry and are not counted
        alert, reason = parse(line, f"{prefix}{seq:06d}")
        seq += 1
        if alert is not None:
            alerts.append(alert)
            result.alerts += 1
        else:
            reason = reason or "unknown"  # a skipped line always carries a reason
            result.skipped += 1
            result.skip_reasons[reason] += 1
            skips.append({"line": i + 1, "reason": reason})
    return alerts, skips


def normalize_mqtt(run_dir: Path, run_id: str, alerts_dir: Path = ALERTS_DIR) -> NormalizeResult:
    """Normalize a run's MQTT logs to `data/alerts/mqtt/<run_id>.parquet`, with a skip log."""
    result = NormalizeResult(run_id=run_id)
    prefix = f"mq-{run_id}-"
    alerts: list[Alert] = []
    skips: list[dict[str, object]] = []

    mqtt_log = run_dir / "mqtt" / "mqtt.log"
    if mqtt_log.is_file():
        a, s = _process(
            mqtt_log.read_text(encoding="utf-8").splitlines(), _publish_alert, prefix, 0, result
        )
        alerts += a
        skips += [{**sk, "source": "mqtt.log"} for sk in s]
    broker_log = run_dir / "mqtt" / "broker.log"
    if broker_log.is_file():
        a, s = _process(
            broker_log.read_text(encoding="utf-8").splitlines(),
            _broker_alert,
            prefix,
            len(alerts) + result.skipped,
            result,
        )
        alerts += a
        skips += [{**sk, "source": "broker.log"} for sk in s]

    out = alerts_dir / "mqtt" / f"{run_id}.parquet"
    write_alerts(alerts, out)
    result.parquet_path = out
    skip_path = alerts_dir / "mqtt" / f"{run_id}.skips.jsonl"
    skip_path.write_text("".join(json.dumps(s) + "\n" for s in skips), encoding="utf-8")
    result.skip_log_path = skip_path
    return result
