"""Tests for the device-keyed bundle assembler (E3-05, SCRUM-64).

The bundle is the unit everything is measured on, so these pin determinism, the window boundary,
empty-window dropping and the source-filter subset property (§4.1, §6.9).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from thesis.assemble.bundles import assemble, bundle_set_hash, write_bundles
from thesis.labels.windows import WindowLabel
from thesis.schema.alert import Alert, FlowDetail, HoneypotDetail, MqttDetail, Source

T0 = datetime(2026, 1, 1, tzinfo=UTC)
W = 60
ALL = {Source.FLOWS, Source.MQTT, Source.HONEYPOT}


def _alert(source: Source, device: str, offset_s: float, aid: str) -> Alert:
    ts = T0 + timedelta(seconds=offset_s)
    if source is Source.FLOWS:
        detail: FlowDetail | MqttDetail | HoneypotDetail = FlowDetail(
            flow_start=ts,
            duration_s=1.0,
            src_ip="a",
            src_port=1,
            dst_ip="b",
            dst_port=2,
            protocol="tcp",
            packets_fwd=1,
            packets_bwd=1,
            bytes_fwd=1,
            bytes_bwd=1,
        )
    elif source is Source.MQTT:
        detail = MqttDetail(event="publish", topic="iot/x/y", payload_bytes=1)
    else:
        detail = HoneypotDetail(event="session_connect", session_id="s", src_ip="a")
    return Alert(alert_id=aid, source=source, ts=ts, subject_device=device, detail=detail)


def _label(device: str, window_index: int, label: str, episode_id: str | None) -> WindowLabel:
    return WindowLabel(device, T0 + timedelta(seconds=window_index * W), label, episode_id)


def test_same_input_gives_the_same_hash() -> None:
    alerts = [_alert(Source.FLOWS, "d1", 10, "a1"), _alert(Source.MQTT, "d1", 20, "a2")]
    labels = [_label("d1", 0, "benign", None)]
    h1 = bundle_set_hash(assemble(alerts, labels, sources=ALL, window_s=W, t0=T0))
    h2 = bundle_set_hash(assemble(alerts, labels, sources=ALL, window_s=W, t0=T0))
    assert h1 == h2 and len(h1) == 64


def test_window_boundary_splits_at_60s() -> None:
    alerts = [_alert(Source.FLOWS, "d1", 59.999, "a1"), _alert(Source.FLOWS, "d1", 60.0, "a2")]
    labels = [_label("d1", 0, "benign", None), _label("d1", 1, "benign", None)]
    bundles = assemble(alerts, labels, sources=ALL, window_s=W, t0=T0)
    assert len(bundles) == 2
    assert {b.window_start for b in bundles} == {T0, T0 + timedelta(seconds=60)}


def test_empty_window_produces_no_bundle() -> None:
    alerts = [_alert(Source.FLOWS, "d1", 10, "a1")]  # only window 0 of d1 has an alert
    # labels exist for several windows, including empty ones, and another device.
    labels = [
        _label("d1", 0, "benign", None),
        _label("d1", 1, "benign", None),
        _label("d2", 0, "benign", None),
    ]
    bundles = assemble(alerts, labels, sources=ALL, window_s=W, t0=T0)
    assert len(bundles) == 1
    assert bundles[0].device == "d1" and bundles[0].window_start == T0


def test_source_filter_is_a_subset_with_same_ids() -> None:
    alerts = [
        _alert(Source.FLOWS, "d1", 10, "f1"),
        _alert(Source.MQTT, "d1", 11, "m1"),
        _alert(Source.HONEYPOT, "d1", 12, "h1"),
        _alert(Source.MQTT, "d2", 10, "m2"),  # d2 window has only MQTT
    ]
    labels = [_label("d1", 0, "benign", None), _label("d2", 0, "benign", None)]
    all_bundles = assemble(alerts, labels, sources=ALL, window_s=W, t0=T0)
    flows_only = assemble(alerts, labels, sources={Source.FLOWS}, window_s=W, t0=T0)

    assert {a.source for b in flows_only for a in b.alerts} == {Source.FLOWS}
    assert {b.bundle_id for b in flows_only} <= {b.bundle_id for b in all_bundles}
    # d2 had only MQTT, so it drops out of the flows-only run.
    assert "d2|" + T0.isoformat() not in {b.bundle_id for b in flows_only}


def test_label_and_episode_id_are_joined() -> None:
    alerts = [_alert(Source.FLOWS, "d1", 10, "f1")]
    labels = [_label("d1", 0, "syn_flood", "ep-syn-001")]
    (bundle,) = assemble(alerts, labels, sources=ALL, window_s=W, t0=T0)
    assert bundle.label == "syn_flood" and bundle.episode_id == "ep-syn-001"
    assert bundle.sources == ("flows",)


def test_window_aligns_to_the_epoch_not_the_first_alert() -> None:
    # First alert at +130 s must land in window 2 ([120,180)), not a window starting at the alert.
    alerts = [_alert(Source.FLOWS, "d1", 130, "f1")]
    labels = [_label("d1", 2, "benign", None)]
    (bundle,) = assemble(alerts, labels, sources=ALL, window_s=W, t0=T0)
    assert bundle.window_start == T0 + timedelta(seconds=120)


def test_write_bundles_round_trips(tmp_path: Path) -> None:
    alerts = [_alert(Source.FLOWS, "d1", 10, "f1"), _alert(Source.MQTT, "d1", 20, "m1")]
    labels = [_label("d1", 0, "benign", None)]
    bundles = assemble(alerts, labels, sources=ALL, window_s=W, t0=T0)
    n = write_bundles(bundles, tmp_path / "bundles.parquet")
    assert n == 1 and (tmp_path / "bundles.parquet").is_file()
