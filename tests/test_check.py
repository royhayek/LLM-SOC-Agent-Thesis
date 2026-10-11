"""Tests for the corpus integrity checks (E2-07, SCRUM-74).

The pure check functions are exercised on synthetic chunks, so each check's pass/fail logic is
pinned without needing the real corpus on disk.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from thesis.corpus import check
from thesis.corpus.check import Chunk, Executed

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _ep(eid: str, family: str, device: str, start_s: int, dur_s: int) -> Executed:
    return Executed(
        eid,
        family,
        device,
        T0 + timedelta(seconds=start_s),
        T0 + timedelta(seconds=start_s + dur_s),
    )


def _chunk(**kw: object) -> Chunk:
    base: dict[str, object] = {
        "run_id": "r",
        "episodes": [],
        "flows": [],
        "cowrie_ts": [],
        "flood_ts": [],
        "brute_ts": [],
        "mqtt_ts": [],
    }
    base.update(kw)
    return Chunk(**base)  # type: ignore[arg-type]


def test_execution_records_pass_and_fail() -> None:
    c = _chunk(episodes=[_ep("a", "syn_flood", "iot-cam-01", 0, 60)])
    ok, _ = check.check_execution_records([c], {"a"})
    assert ok
    ok2, detail = check.check_execution_records([c], {"a", "b"})
    assert not ok2 and "missing" in detail and "b" in detail


def test_source_traces_honeypot_family() -> None:
    vis = {"ssh_brute_force": {"mqtt": False, "flows": True, "honeypot": True}}
    atk = check.ATTACKER_IP
    ep = _ep("s1", "ssh_brute_force", "hp-ssh-01", 0, 60)
    # flow (attacker involved) overlapping + a honeypot event in window -> pass
    good = _chunk(
        episodes=[ep],
        flows=[(T0, T0 + timedelta(seconds=60), atk, "10.77.0.10")],
        cowrie_ts=[T0 + timedelta(seconds=5)],
    )
    assert check.check_source_traces([good], vis, "192.0.2.1")[0]
    # no honeypot event -> fail, names the episode
    bad = _chunk(episodes=[ep], flows=[(T0, T0 + timedelta(seconds=60), atk, "10.77.0.10")])
    ok, detail = check.check_source_traces([bad], vis, "192.0.2.1")
    assert not ok and "s1" in detail


def test_source_traces_mqtt_flood_uses_device_flow() -> None:
    vis = {"mqtt_publish_flood": {"mqtt": True, "flows": True, "honeypot": False}}
    dev_ip = check.SERVICE_IP[check.DEVICE_SERVICE["iot-temp-01"]]
    ep = _ep("f1", "mqtt_publish_flood", "iot-temp-01", 0, 120)
    chunk = _chunk(
        episodes=[ep],
        flows=[(T0, T0 + timedelta(seconds=300), dev_ip, "10.77.0.2")],  # device->broker, overlaps
        flood_ts=[T0 + timedelta(seconds=10)],
    )
    assert check.check_source_traces([chunk], vis, "192.0.2.1")[0]


def test_source_traces_botnet_uses_c2() -> None:
    vis = {"botnet": {"mqtt": False, "flows": True, "honeypot": False}}
    ep = _ep("b1", "botnet", "iot-cam-01", 0, 90)
    chunk = _chunk(
        episodes=[ep], flows=[(T0, T0 + timedelta(seconds=90), "10.77.0.22", "192.0.2.1")]
    )
    assert check.check_source_traces([chunk], vis, "192.0.2.1")[0]


def test_no_overlap_pass_and_fail() -> None:
    a = _ep("a", "ssh_brute_force", "hp-ssh-01", 0, 60)
    b = _ep("b", "port_scan", "hp-ssh-01", 60, 60)  # adjacent, allowed
    assert check.check_no_overlap([_chunk(episodes=[a, b])])[0]
    c = _ep("c", "port_scan", "hp-ssh-01", 30, 60)  # overlaps a
    ok, detail = check.check_no_overlap([_chunk(episodes=[a, c])])
    assert not ok and "hp-ssh-01" in detail


def test_capture_gaps_pass_and_fail() -> None:
    dense = [T0 + timedelta(seconds=i * 5) for i in range(20)]  # 5 s apart
    assert check.check_capture_gaps([_chunk(mqtt_ts=dense)], 60)[0]
    sparse = [T0, T0 + timedelta(seconds=120)]  # 120 s gap > 60
    ok, detail = check.check_capture_gaps([_chunk(mqtt_ts=sparse)], 60)
    assert not ok and "120" in detail
