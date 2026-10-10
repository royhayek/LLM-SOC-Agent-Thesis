"""Helpers for the attack-family `slow` tests (E1-08..E1-13).

Each family's slow test runs a one-episode schedule twice with the same seed and compares the
raw event counts per source against the tolerance in `attack_tolerance.yaml`. Run these with
Ollama stopped and under `caffeinate -is` (a host that sleeps freezes the Docker VM).
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import yaml

from thesis.scenario.families import default_registry
from thesis.scenario.families.base import DEVICE_SERVICE, SERVICE_IP
from thesis.scenario.runner import run_scenario
from thesis.scenario.schedule import Episode, Schedule

REPO_ROOT = Path(__file__).resolve().parent.parent
TOLERANCE = yaml.safe_load((Path(__file__).resolve().parent / "attack_tolerance.yaml").read_text())
HOST_SLEEP_SLACK_S = 30


def run_family_episode(family: str, device: str, duration_s: int, seed: int, **params: Any) -> Path:
    """Run one episode of `family` against `device` on the real testbed; return the run folder."""
    assert not (REPO_ROOT / "data" / "raw" / ".current_run").exists(), "a run is already up"
    schedule = Schedule(
        episodes=(
            Episode(
                id=f"ep-{family}",
                family=family,  # type: ignore[arg-type]  # validated by the model
                target_device=device,
                start_offset_s=8,
                duration_s=duration_s,
                parameters=params,
                seed=seed,
            ),
        )
    )
    wall0, mono0 = time.time(), time.monotonic()
    result = run_scenario(schedule, registry=default_registry())
    slept = (time.time() - wall0) - (time.monotonic() - mono0)
    assert slept <= HOST_SLEEP_SLACK_S, f"the host slept ~{slept:.0f}s during the run; rerun awake"
    assert not result.aborted, "the isolation gate aborted the run"
    assert result.valid, "the run was marked invalid"
    return result.run_dir


def device_ip(device: str) -> str:
    return SERVICE_IP[DEVICE_SERVICE[device]]


def count_mqtt_topic(run_dir: Path, topic_substring: str) -> int:
    log = (run_dir / "mqtt" / "mqtt.log").read_text(encoding="utf-8")
    return sum(1 for line in log.splitlines() if topic_substring in line)


def count_flows_for_ip(run_dir: Path, ip: str) -> int:
    n = 0
    for line in (run_dir / "flows" / "flows.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        flow = json.loads(line)
        if ip in (flow.get("src_ip"), flow.get("dst_ip")):
            n += 1
    return n


def count_broker_refused(run_dir: Path, client_substring: str) -> int:
    """Refused-auth lines in the broker log for a given client id (E1-05 keeps broker.log)."""
    log = run_dir / "mqtt" / "broker.log"
    if not log.is_file():
        return 0
    return sum(
        1
        for line in log.read_text(encoding="utf-8").splitlines()
        if "not authori" in line and client_substring in line
    )


def count_packets_to_port(run_dir: Path, dst_ip: str, dst_port: int) -> int:
    """Total packets across flows to dst_ip:dst_port (both directions). Used for flood volume."""
    total = 0
    for line in (run_dir / "flows" / "flows.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        f = json.loads(line)
        if f.get("dst_ip") == dst_ip and f.get("dst_port") == dst_port:
            total += int(f.get("src2dst_packets", 0)) + int(f.get("dst2src_packets", 0))
    return total


def count_packets_to_ip(run_dir: Path, dst_ip: str) -> int:
    """Total packets across flows whose destination is dst_ip (both directions). Used for the
    botnet replay, whose retargeted destination is a fixed non-routable address."""
    total = 0
    for line in (run_dir / "flows" / "flows.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        f = json.loads(line)
        if f.get("dst_ip") == dst_ip:
            total += int(f.get("src2dst_packets", 0)) + int(f.get("dst2src_packets", 0))
    return total


def count_flows_to_ip(run_dir: Path, dst_ip: str) -> int:
    return sum(
        1
        for line in (run_dir / "flows" / "flows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("dst_ip") == dst_ip
    )


def count_honeypot_events(run_dir: Path) -> int:
    path = run_dir / "honeypot" / "cowrie.json"
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def within_tolerance(family: str, source: str, a: int, b: int) -> bool:
    """True if counts a and b are within the family/source tolerance (fraction of a, with an
    absolute floor)."""
    frac = TOLERANCE["families"][family][source]
    floor = TOLERANCE["defaults"]["abs_floor"]
    return abs(a - b) <= max(floor, math.ceil(frac * a))
