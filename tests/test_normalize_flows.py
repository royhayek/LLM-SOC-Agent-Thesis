"""Tests for the flow normalizer (E3-03, SCRUM-38).

Fixtures use the placeholder device/infrastructure IPs of `devices.py` (the real 10.77.0.x
inventory is E5-01). The count invariant guards against silent dropping (§6.9); the device-keying
cases are the ones that would otherwise put evidence in the wrong bundle.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from thesis.normalize.flows import normalize_flows
from thesis.normalize.store import read_alerts

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "raw"


def _run_dir(tmp_path: Path) -> Path:
    flows = tmp_path / "run" / "flows"
    flows.mkdir(parents=True)
    shutil.copy(FIXTURES / "flows_sample.jsonl", flows / "flows.jsonl")
    return tmp_path / "run"


def _alerts(tmp_path: Path) -> list:
    result = normalize_flows(_run_dir(tmp_path), "r1", alerts_dir=tmp_path / "alerts")
    assert result.parquet_path is not None
    return read_alerts(result.parquet_path)


def test_alerts_plus_skipped_equals_records(tmp_path: Path) -> None:
    result = normalize_flows(_run_dir(tmp_path), "r1", alerts_dir=tmp_path / "alerts")
    assert result.lines == 5
    assert result.alerts == 2  # emulator<->broker and attacker->honeypot
    assert result.skipped == 3  # infra-only, device-to-device, malformed


def test_emulator_to_broker_keys_to_the_emulator(tmp_path: Path) -> None:
    alerts = _alerts(tmp_path)
    broker_flow = [a for a in alerts if a.detail.dst_port == 1883]  # type: ignore[union-attr]
    assert broker_flow and broker_flow[0].subject_device == "iot-temp-01"


def test_infrastructure_only_flow_is_skipped_with_reason(tmp_path: Path) -> None:
    result = normalize_flows(_run_dir(tmp_path), "r1", alerts_dir=tmp_path / "alerts")
    assert result.skip_reasons["infrastructure_only"] == 1
    assert result.skip_reasons["device_to_device"] == 1
    assert result.skip_reasons["malformed"] == 1


def test_attacker_to_honeypot_keys_to_the_honeypot(tmp_path: Path) -> None:
    alerts = _alerts(tmp_path)
    hp = [a for a in alerts if a.detail.dst_port == 22]  # type: ignore[union-attr]
    assert hp and hp[0].subject_device == "hp-ssh-01"


def test_syn_counts_and_flags_are_carried(tmp_path: Path) -> None:
    alerts = _alerts(tmp_path)
    hp = [a for a in alerts if a.detail.dst_port == 22][0]  # type: ignore[union-attr]
    assert hp.detail.syn_count_fwd == 1 and hp.detail.ack_count_fwd == 0  # type: ignore[union-attr]
    assert hp.detail.tcp_flags == "SYN"  # type: ignore[union-attr]


def test_parquet_written_at_the_flows_path(tmp_path: Path) -> None:
    result = normalize_flows(_run_dir(tmp_path), "run-xyz", alerts_dir=tmp_path / "alerts")
    assert result.parquet_path == tmp_path / "alerts" / "flows" / "run-xyz.parquet"
    assert result.parquet_path.is_file()
