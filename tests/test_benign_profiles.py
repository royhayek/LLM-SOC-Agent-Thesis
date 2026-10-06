"""Tests for the benign traffic profiles (E1-05).

Fast tests check the profile file, the seeded plan generator and the log readers. The two
`slow` tests run the real testbed: the seed test (two 10-minute runs with one seed give the
same message sequences) and the 30-minute rate test (each irregularity within tolerance).
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from thesis.testbed.benign import (
    PROFILE_PATH,
    MqttMessage,
    PlanEvent,
    count_broker_events,
    count_bursts,
    expected_counts,
    generate_plans,
    load_profile,
    message_sequences,
    observed_counts,
    parse_mqtt_log,
    rate_failures,
    write_plans,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE = REPO_ROOT / "docker-compose.yml"
CREDENTIALS = REPO_ROOT / "testbed" / "broker" / "credentials.txt"


def _counts(plan_events: Sequence[PlanEvent]) -> dict[str, int]:
    out = {"reconnect": 0, "badauth": 0}
    for e in plan_events:
        if e.action in out:
            out[e.action] += 1
    return out


# --- The profile file ---------------------------------------------------------------------


def test_every_profile_parameter_has_a_comment() -> None:
    """Every line that sets a value carries a `#` comment explaining it (E1-05 AC)."""
    for n, line in enumerate(PROFILE_PATH.read_text(encoding="utf-8").splitlines(), 1):
        body = line.split("#", 1)[0].strip()
        if not body or ":" not in body:
            continue
        value = body.split(":", 1)[1].strip()
        if value:  # a key with a value, not a bare container key
            assert "#" in line, f"line {n} has no comment: {line!r}"


def test_profile_states_its_tolerance() -> None:
    assert load_profile().tolerance == 0.25


def test_compose_matches_profile_and_credentials() -> None:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    creds = dict(
        line.split(":", 1)
        for line in CREDENTIALS.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )
    emulators = {
        s["environment"]["DEVICE_ID"]: s["environment"]["PASSWORD"]
        for name, s in compose["services"].items()
        if name.startswith("emulator-")
    }
    assert set(emulators) == {e.device_id for e in load_profile().emulators}
    for device, password in emulators.items():
        assert creds[device] == password, device
    logger_cmd = " ".join(compose["services"]["mqtt-logger"]["command"])
    assert f"-P {creds['mqtt-logger']}" in logger_cmd


# --- The plan generator -------------------------------------------------------------------


def test_same_seed_gives_the_same_plans() -> None:
    profile = load_profile()
    assert generate_plans(profile, seed=7, duration_s=600) == generate_plans(
        profile, seed=7, duration_s=600
    )


def test_different_seed_gives_different_plans() -> None:
    profile = load_profile()
    assert generate_plans(profile, seed=7, duration_s=600) != generate_plans(
        profile, seed=8, duration_s=600
    )


def test_irregularities_are_exact_over_whole_slots() -> None:
    """Over 30 minutes every emulator holds exactly rate × 0.5 h of each irregularity."""
    profile = load_profile()
    plans = generate_plans(profile, duration_s=1800)
    for emulator in profile.emulators:
        irr = profile.irregularities_for(emulator)
        counts = _counts(plans[emulator.device_id].events)
        assert counts["reconnect"] == irr.reconnect_per_hour // 2
        assert counts["badauth"] == irr.wrong_password_per_hour // 2


def test_plans_respect_the_profile() -> None:
    profile = load_profile()
    plans = generate_plans(profile, duration_s=1800)
    for emulator in profile.emulators:
        plan = plans[emulator.device_id]
        assert [qos for _, qos in plan.topics] == [t.qos for t in emulator.topics]
        offsets = [e.offset_ms for e in plan.events]
        assert offsets == sorted(offsets)
        assert all(profile.start_delay_s * 1000 <= o < 1800 * 1000 for o in offsets)
        for e in plan.events:
            if e.action != "pub":
                continue
            assert e.topic_index is not None and e.payload is not None
            low, high = emulator.topics[e.topic_index].payload_bytes
            assert low <= len(e.payload.encode()) <= high
            assert " " not in e.payload  # a plan line splits on spaces


def test_write_plans_writes_one_plan_per_emulator(tmp_path: Path) -> None:
    write_plans(PROFILE_PATH, tmp_path, seed=3, duration_s=120)
    for emulator in load_profile().emulators:
        assert (tmp_path / f"{emulator.device_id}.plan").is_file()
        assert (tmp_path / f"{emulator.device_id}.topics").is_file()
    manifest = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert '"seed": 3' in manifest and '"duration_s": 120' in manifest


# --- Reading a run back -------------------------------------------------------------------


def _msg(second: float, topic: str = "iot/d1/telemetry", size: int = 10) -> MqttMessage:
    ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=int(second))
    return MqttMessage(ts, topic, size)


def test_parse_mqtt_log(tmp_path: Path) -> None:
    log = tmp_path / "mqtt.log"
    log.write_text('2026-10-06T17:00:45+0000 iot/dev/telemetry {"n":1}\n', encoding="utf-8")
    [m] = parse_mqtt_log(log)
    assert m.topic == "iot/dev/telemetry" and m.size == 7 and m.device_id == "dev"


def test_sequences_count_offsets_from_each_devices_first_message() -> None:
    msgs = [_msg(100, "iot/a/telemetry"), _msg(105, "iot/a/telemetry", 12), _msg(3, "iot/b/status")]
    seqs = message_sequences(msgs)
    assert seqs["a"] == [("iot/a/telemetry", 10, 0), ("iot/a/telemetry", 12, 5)]
    assert seqs["b"] == [("iot/b/status", 10, 0)]


def test_count_bursts() -> None:
    regular = [_msg(t) for t in (0, 5, 10)]
    burst = [_msg(20), _msg(20), _msg(21)]  # three within one second of each other
    pair = [_msg(40), _msg(40)]  # two only: not a burst
    assert count_bursts(regular + burst + pair) == 1


def _connected(ts: str, client: str, user: str) -> str:
    """A broker log line in the format mosquitto 2.0.22 writes (checked on a live broker)."""
    return f"{ts}: New client connected from 10.77.0.21:1 as {client} (p2, c1, k60, u'{user}')."


def test_count_broker_events(tmp_path: Path) -> None:
    log = tmp_path / "broker.log"
    lines = [
        _connected("2026-10-06T17:00:44", "mqtt-logger", "mqtt-logger"),
        _connected("2026-10-06T17:00:45", "d1-t0", "d1"),
        _connected("2026-10-06T17:00:45", "d1-t1", "d1"),
        "2026-10-06T17:01:00: Client d1-t0 disconnected.",
        _connected("2026-10-06T17:01:00", "d1-t0", "d1"),
        "2026-10-06T17:01:05: Client d1-auth disconnected, not authorised.",
    ]
    log.write_text("\n".join(lines), encoding="utf-8")
    assert count_broker_events(log) == (1, 1)


def test_rate_failures() -> None:
    expected = {"reconnect": 8.0, "burst": 12.0, "wrong_password": 4.0}
    assert rate_failures({"reconnect": 8, "burst": 10, "wrong_password": 4}, expected, 0.25) == []
    assert rate_failures({"reconnect": 5, "burst": 12, "wrong_password": 4}, expected, 0.25) != []


# --- Real testbed runs (slow) -------------------------------------------------------------


# More than this much wall-clock time beyond the monotonic clock means the host slept.
HOST_SLEEP_SLACK_S = 30


def _benign_run(seconds: int, **env: str) -> Path:
    """`make up`, wait, `make down`; return the run folder. Ollama must be stopped.

    If the host sleeps, the Docker VM freezes and the run's message offsets gain a gap, so
    the run cannot be compared. The monotonic clock stops during sleep and the wall clock
    does not; a difference between them fails the run with that reason. Run these tests
    under `caffeinate -is` on macOS.
    """
    assert not (REPO_ROOT / "data" / "raw" / ".current_run").exists(), "a run is already up"
    subprocess.run(["make", "up"], cwd=REPO_ROOT, env={**os.environ, **env}, check=True)
    run_id = (REPO_ROOT / "data" / "raw" / ".current_run").read_text(encoding="utf-8").strip()
    wall0, mono0 = time.time(), time.monotonic()
    try:
        time.sleep(seconds)
    finally:
        subprocess.run(["make", "down"], cwd=REPO_ROOT, check=True)
    slept = (time.time() - wall0) - (time.monotonic() - mono0)
    if slept > HOST_SLEEP_SLACK_S:
        pytest.fail(f"the host slept about {slept:.0f} s during run {run_id}; rerun awake")
    return REPO_ROOT / "data" / "raw" / run_id


@pytest.mark.slow
def test_same_seed_two_10_minute_runs_give_identical_sequences() -> None:
    """The seed test (E1-05 AC): two 10-minute benign runs with the same seed give identical
    per-emulator message sequences (topic, size, offset from the emulator's first message).
    The plan is cut at 600 s and each run lasts a little longer, so both runs replay it whole.
    """
    env = {"BENIGN_SEED": "4242", "BENIGN_DURATION_S": "600"}
    a = message_sequences(parse_mqtt_log(_benign_run(630, **env) / "mqtt" / "mqtt.log"))
    b = message_sequences(parse_mqtt_log(_benign_run(630, **env) / "mqtt" / "mqtt.log"))
    assert set(a) == {e.device_id for e in load_profile().emulators}
    assert all(len(seq) > 50 for seq in a.values())
    assert a == b


@pytest.mark.slow
def test_30_minute_run_irregularities_within_tolerance() -> None:
    """Each irregularity type appears at its configured rate within the profile's tolerance."""
    profile = load_profile()
    run_dir = _benign_run(1830, BENIGN_DURATION_S="1800")
    failures = rate_failures(
        observed_counts(run_dir), expected_counts(profile, 1800), profile.tolerance
    )
    assert failures == []
