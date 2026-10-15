"""Tests for the frozen reduction policy (E3-06, SCRUM-77)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from thesis.assemble.bundles import Bundle
from thesis.reduce.policy import FLOW_EXEMPLARS, POLICY_VERSION, reduce, to_json
from thesis.schema.alert import Alert, FlowDetail, HoneypotDetail, MqttDetail, Source

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _flow(aid: str, score: float, ts_off: int = 0) -> Alert:
    return Alert(
        alert_id=aid,
        source="flows",
        ts=T0 + timedelta(seconds=ts_off),
        subject_device="iot-cam-01",
        detector_score=score,
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
            syn_count_fwd=10,
            ack_count_fwd=0,
        ),
    )


def _hp(aid: str, event: str, session: str, command: str | None = None) -> Alert:
    return Alert(
        alert_id=aid,
        source="honeypot",
        ts=T0,
        subject_device="hp-ssh-01",
        detector_score=0.8,
        detector_label=event,
        detector_name="honeypot_rules",
        detail=HoneypotDetail(
            event=event, session_id=session, src_ip="10.77.0.30", src_port=22, command=command
        ),
    )


def _bundle(alerts: list[Alert], device: str = "iot-cam-01") -> Bundle:
    return Bundle(
        bundle_id=f"{device}|{T0.isoformat()}",
        device=device,
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="syn_flood",
        episode_id="ep-1",
        sources=tuple(sorted({a.source.value for a in alerts})),
        alerts=tuple(alerts),
    )


def test_reduce_is_byte_identical() -> None:
    b = _bundle([_flow("f1", 0.9), _flow("f2", 0.5)])
    assert to_json(reduce(b)) == to_json(reduce(b))
    assert POLICY_VERSION == "reduction-v1.0"


def test_flow_exemplars_capped_and_ordered_by_score() -> None:
    alerts = [_flow(f"f{i}", score=i / 10, ts_off=i) for i in range(10)]
    view = reduce(_bundle(alerts))
    flows = view["flows"]
    exemplars = flows["exemplars"]  # type: ignore[index]
    assert len(exemplars) == FLOW_EXEMPLARS
    scores = [e["score"] for e in exemplars]
    assert scores == sorted(scores, reverse=True)  # descending by detector score


def test_honeypot_command_is_capped() -> None:
    long_cmd = "A" * 500
    b = _bundle([_hp("c1", "command", "s1", command=long_cmd)], device="hp-ssh-01")
    seq = view_cmd(reduce(b))
    assert len(seq) <= 200 + len("…[+300 chars]") and "…[+300 chars]" in seq


def view_cmd(view: dict) -> str:  # type: ignore[type-arg]
    return view["honeypot"]["exemplars"][0]["cmd"]  # type: ignore[index]


def test_no_mqtt_alerts_states_no_alerts_not_omitted() -> None:
    b = _bundle([_flow("f1", 0.9)])
    view = reduce(b, sources=(Source.FLOWS, Source.MQTT, Source.HONEYPOT))
    assert view["sources"]["mqtt"] == "no_alerts"  # type: ignore[index]
    assert "mqtt" not in view  # no block for a no_alerts source; the state carries it


def test_source_not_in_config_is_marked() -> None:
    b = _bundle([_flow("f1", 0.9)])
    view = reduce(b, sources=(Source.FLOWS,))
    assert view["sources"]["mqtt"] == "not_in_config"  # type: ignore[index]
    assert view["sources"]["flows"] == "active"  # type: ignore[index]


def test_mqtt_block_present_when_active() -> None:
    mqtt = Alert(
        alert_id="m1",
        source="mqtt",
        ts=T0,
        subject_device="iot-temp-01",
        detector_score=1.0,
        detector_label="novel_topic",
        detector_name="mqtt_thresholds",
        detail=MqttDetail(event="publish", topic="iot/iot-temp-01/flood", payload_bytes=10),
    )
    view = reduce(_bundle([mqtt], device="iot-temp-01"))
    assert view["sources"]["mqtt"] == "active"  # type: ignore[index]
    assert view["mqtt"]["message_count"] == 1  # type: ignore[index]
