"""Benign traffic profiles for the MQTT emulators (E1-05; record §4.1).

`testbed/profiles/benign.yaml` describes each emulator: its topics (period, jitter, QoS,
payload size range) and its benign irregularities (reconnects, bursts, wrong passwords).
`generate_plans()` turns the profile and a seed into one plan per emulator: a list of timed
events. `make up` writes the plans into the run folder and each emulator replays its own,
so the same seed gives the same messages (topic, size, offset) in every run.

Irregularities are placed one per slot: an event at rate r per hour falls at a seeded,
uniform point in the first 80 % of each slot of 3600 / r seconds. A run of whole slots
therefore holds exactly r events per hour per emulator, and the ±tolerance in the profile
only has to absorb what the testbed loses, not sampling noise.

The second half of the module reads a run's logs back: the message sequence per emulator
(`mqtt/mqtt.log`) and the irregularity counts (`mqtt/mqtt.log` for bursts,
`mqtt/broker.log` for reconnects and refused passwords).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Final, Literal, NamedTuple, Self

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator

REPO_ROOT: Final = Path(__file__).resolve().parent.parent.parent
PROFILE_PATH: Final = REPO_ROOT / "testbed" / "profiles" / "benign.yaml"
# The emulator opens one connection per topic on file descriptors 3 and 4 (emulate.sh).
MAX_TOPICS: Final = 2
# Gaps of one logged second or less join messages into one cluster (see count_bursts).
CLUSTER_GAP_S: Final = 1
# Regular readings must be further apart than a cluster gap, or they would look like a burst.
MIN_REGULAR_GAP_S: Final = 3
# Irregularities fall in the first 80 % of their slot, so a run of whole slots holds them all.
SLOT_SPREAD: Final = 0.8


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TopicProfile(_Strict):
    name: str = Field(pattern=r"^[a-z]+$")
    period_s: int = Field(gt=0, strict=True)
    jitter_s: int = Field(ge=0, strict=True)
    qos: Literal[0, 1, 2]
    payload_bytes: tuple[int, int]

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.period_s - self.jitter_s < MIN_REGULAR_GAP_S:
            raise ValueError(f"{self.name}: period_s - jitter_s must be >= {MIN_REGULAR_GAP_S}")
        low, high = self.payload_bytes
        if not 0 < low <= high:
            raise ValueError(f"{self.name}: payload_bytes must be 0 < min <= max")
        return self


class Irregularities(_Strict):
    reconnect_per_hour: int = Field(ge=0, strict=True)
    burst_per_hour: int = Field(ge=0, strict=True)
    burst_size: tuple[int, int]
    wrong_password_per_hour: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def _check(self) -> Self:
        for name in ("reconnect_per_hour", "burst_per_hour", "wrong_password_per_hour"):
            rate = getattr(self, name)
            if rate and 3600 % rate:
                raise ValueError(f"{name} must divide 3600, so every slot is whole seconds")
        low, high = self.burst_size
        if not 3 <= low <= high:
            raise ValueError("burst_size must be 3 <= min <= max, so a burst is countable")
        return self


class EmulatorProfile(_Strict):
    device_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    base_value: float
    topics: tuple[TopicProfile, ...] = Field(min_length=1, max_length=MAX_TOPICS)
    irregularities: Irregularities | None = None

    @model_validator(mode="after")
    def _unique_topics(self) -> Self:
        names = [t.name for t in self.topics]
        if len(names) != len(set(names)):
            raise ValueError(f"{self.device_id}: duplicate topic names")
        return self


class _Defaults(_Strict):
    irregularities: Irregularities


class BenignProfile(_Strict):
    version: str
    seed: int = Field(ge=0, strict=True)
    tolerance: float = Field(gt=0, lt=1)
    start_delay_s: int = Field(ge=0, strict=True)
    plan_duration_s: int = Field(gt=0, strict=True)
    burst_spacing_ms: int = Field(gt=0, strict=True)
    defaults: _Defaults
    emulators: tuple[EmulatorProfile, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> Self:
        ids = [e.device_id for e in self.emulators]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate device_id")
        for e in self.emulators:
            spread = (self.irregularities_for(e).burst_size[1] - 1) * self.burst_spacing_ms
            if spread >= 500:
                raise ValueError(f"{e.device_id}: a burst must span under 0.5 s")
        return self

    def irregularities_for(self, emulator: EmulatorProfile) -> Irregularities:
        return emulator.irregularities or self.defaults.irregularities


def load_profile(path: Path = PROFILE_PATH) -> BenignProfile:
    with path.open(encoding="utf-8") as f:
        return BenignProfile.model_validate(yaml.safe_load(f))


# --- Plans -------------------------------------------------------------------------------

Action = Literal["pub", "reconnect", "badauth"]
_ACTION_ORDER: Final[dict[str, int]] = {"reconnect": 0, "badauth": 1, "pub": 2}


class PlanEvent(NamedTuple):
    offset_ms: int
    action: Action
    topic_index: int | None = None
    payload: str | None = None

    def line(self) -> str:
        if self.action == "pub":
            return f"{self.offset_ms} pub {self.topic_index} {self.payload}"
        return f"{self.offset_ms} {self.action} - -"


class EmulatorPlan(NamedTuple):
    device_id: str
    topics: tuple[tuple[str, int], ...]  # (full topic, qos) per topic index
    events: tuple[PlanEvent, ...]


def _rng(seed: int, device_id: str, purpose: str) -> random.Random:
    """One independent, seeded stream per device and purpose, so changing one part of a
    profile does not shift the random draws of another."""
    return random.Random(f"{seed}:{device_id}:{purpose}")


def _slot_offsets(
    rate_per_hour: int, start_s: int, duration_s: int, rng: random.Random
) -> list[int]:
    """Whole-second offsets, one per slot of 3600 / rate seconds, before `duration_s`."""
    if rate_per_hour == 0:
        return []
    interval = 3600 // rate_per_hour
    offsets = []
    k = 0
    while start_s + k * interval < duration_s:
        offset = start_s + k * interval + int(rng.uniform(0, SLOT_SPREAD * interval))
        if offset < duration_s:
            offsets.append(offset)
        k += 1
    return offsets


def _payload(emulator: EmulatorProfile, topic: TopicProfile, seq: int, rng: random.Random) -> str:
    """Compact JSON (no spaces, so a plan line splits cleanly), padded to a drawn size."""
    if topic.name == "telemetry":
        value = round(emulator.base_value * (1 + (rng.random() - 0.5) * 0.1), 2)
        body: dict[str, object] = {
            "device_id": emulator.device_id,
            "kind": emulator.kind,
            "seq": seq,
            "value": value,
        }
    else:
        body = {"device_id": emulator.device_id, "status": "ok", "seq": seq}
    size = rng.randint(*topic.payload_bytes)
    base = json.dumps({**body, "pad": ""}, separators=(",", ":"))
    if len(base) > size:
        raise ValueError(f"{emulator.device_id}/{topic.name}: payload_bytes below {len(base)}")
    return json.dumps({**body, "pad": "x" * (size - len(base))}, separators=(",", ":"))


def generate_plan(
    profile: BenignProfile, emulator: EmulatorProfile, seed: int, duration_s: int
) -> EmulatorPlan:
    """The emulator's events from `start_delay_s` to `duration_s`, in time order."""
    irr = profile.irregularities_for(emulator)
    start = profile.start_delay_s

    # (offset_ms, topic_index) of every publish, regular and burst.
    pubs: list[tuple[int, int]] = []
    for idx, topic in enumerate(emulator.topics):
        rng = _rng(seed, emulator.device_id, f"regular:{topic.name}")
        t = start + rng.randint(0, topic.period_s - 1)
        while t < duration_s:
            pubs.append((t * 1000, idx))
            t += topic.period_s + rng.randint(-topic.jitter_s, topic.jitter_s)

    burst_rng = _rng(seed, emulator.device_id, "burst")
    for b in _slot_offsets(irr.burst_per_hour, start, duration_s, burst_rng):
        for i in range(burst_rng.randint(*irr.burst_size)):
            pubs.append((b * 1000 + i * profile.burst_spacing_ms, 0))

    events: list[PlanEvent] = []
    payload_rng = _rng(seed, emulator.device_id, "payload")
    seq = dict.fromkeys(range(len(emulator.topics)), 0)
    for offset_ms, idx in sorted(pubs):
        seq[idx] += 1
        payload = _payload(emulator, emulator.topics[idx], seq[idx], payload_rng)
        events.append(PlanEvent(offset_ms, "pub", idx, payload))

    reconnect_rng = _rng(seed, emulator.device_id, "reconnect")
    for r in _slot_offsets(irr.reconnect_per_hour, start, duration_s, reconnect_rng):
        events.append(PlanEvent(r * 1000, "reconnect"))
    auth_rng = _rng(seed, emulator.device_id, "badauth")
    for a in _slot_offsets(irr.wrong_password_per_hour, start, duration_s, auth_rng):
        events.append(PlanEvent(a * 1000, "badauth"))

    events.sort(key=lambda e: (e.offset_ms, _ACTION_ORDER[e.action], e.topic_index or 0))
    topics = tuple((f"iot/{emulator.device_id}/{t.name}", t.qos) for t in emulator.topics)
    return EmulatorPlan(emulator.device_id, topics, tuple(events))


def generate_plans(
    profile: BenignProfile, seed: int | None = None, duration_s: int | None = None
) -> dict[str, EmulatorPlan]:
    seed = profile.seed if seed is None else seed
    duration_s = profile.plan_duration_s if duration_s is None else duration_s
    return {e.device_id: generate_plan(profile, e, seed, duration_s) for e in profile.emulators}


def write_plans(
    profile_path: Path, out_dir: Path, seed: int | None = None, duration_s: int | None = None
) -> None:
    """Write `<device>.plan`, `<device>.topics` and `manifest.json` into `out_dir`."""
    profile = load_profile(profile_path)
    plans = generate_plans(profile, seed, duration_s)
    out_dir.mkdir(parents=True, exist_ok=True)
    for device_id, plan in plans.items():
        (out_dir / f"{device_id}.topics").write_text(
            "".join(f"{i} {topic} {qos}\n" for i, (topic, qos) in enumerate(plan.topics)),
            encoding="utf-8",
        )
        (out_dir / f"{device_id}.plan").write_text(
            "".join(e.line() + "\n" for e in plan.events), encoding="utf-8"
        )
    manifest = {
        "profile": str(profile_path.name),
        "profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        "version": profile.version,
        "seed": profile.seed if seed is None else seed,
        "duration_s": profile.plan_duration_s if duration_s is None else duration_s,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


# --- Reading a run back ------------------------------------------------------------------


class MqttMessage(NamedTuple):
    ts: datetime  # the MQTT logger's receive time, whole seconds
    topic: str
    size: int  # payload size in bytes

    @property
    def device_id(self) -> str:
        return self.topic.split("/")[1]


def parse_mqtt_log(path: Path) -> list[MqttMessage]:
    """Parse the logger's `%I %t %p` lines: ISO time, topic, payload."""
    messages = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ts, topic, payload = (line.split(" ", 2) + [""])[:3]
        messages.append(
            MqttMessage(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z"), topic, len(payload.encode()))
        )
    return messages


Sequences = dict[str, list[tuple[str, int, int]]]


def message_sequences(messages: Sequence[MqttMessage]) -> Sequences:
    """Per emulator, its messages as (topic, size, offset_s), the offset counted from that
    emulator's own first message, so container start-up jitter cancels out (E1-05 gotcha)."""
    by_device: dict[str, list[MqttMessage]] = defaultdict(list)
    for m in messages:
        by_device[m.device_id].append(m)
    out: Sequences = {}
    for device, msgs in sorted(by_device.items()):
        first = msgs[0].ts
        out[device] = [(m.topic, m.size, int((m.ts - first).total_seconds())) for m in msgs]
    return out


def count_bursts(messages: Sequence[MqttMessage], min_size: int = 3) -> int:
    """Clusters of `min_size` or more messages on one topic whose gaps are all at most one
    logged second. Regular readings are further apart, so they never form a cluster alone."""
    by_topic: dict[str, list[datetime]] = defaultdict(list)
    for m in messages:
        by_topic[m.topic].append(m.ts)
    bursts = 0
    for stamps in by_topic.values():
        stamps.sort()
        size = 1
        for prev, cur in zip(stamps, stamps[1:], strict=False):
            if (cur - prev).total_seconds() <= CLUSTER_GAP_S:
                size += 1
                continue
            bursts += size >= min_size
            size = 1
        bursts += size >= min_size
    return bursts


_CONNECTED = re.compile(r": New client connected from \S+ as (\S+) ")
_REFUSED = re.compile(r": Client (\S+) disconnected, not authori[sz]ed\.")


def count_broker_events(broker_log: Path) -> tuple[int, int]:
    """(reconnects, refused passwords) from the broker log.

    A reconnect is every connection of an emulator's first-topic client (`<device>-t0`) after
    its first. A refused password is a refused CONNECT from an emulator's `<device>-auth` client.
    """
    connects: dict[str, int] = defaultdict(int)
    refused = 0
    for line in broker_log.read_text(encoding="utf-8").splitlines():
        if (m := _CONNECTED.search(line)) and m.group(1).endswith("-t0"):
            connects[m.group(1)] += 1
        elif (m := _REFUSED.search(line)) and m.group(1).endswith("-auth"):
            refused += 1
    return sum(max(0, n - 1) for n in connects.values()), refused


def observed_counts(run_dir: Path, min_burst: int = 3) -> dict[str, int]:
    reconnects, refused = count_broker_events(run_dir / "mqtt" / "broker.log")
    bursts = count_bursts(parse_mqtt_log(run_dir / "mqtt" / "mqtt.log"), min_burst)
    return {"reconnect": reconnects, "burst": bursts, "wrong_password": refused}


def expected_counts(profile: BenignProfile, duration_s: int) -> dict[str, float]:
    hours = duration_s / 3600
    out = {"reconnect": 0.0, "burst": 0.0, "wrong_password": 0.0}
    for e in profile.emulators:
        irr = profile.irregularities_for(e)
        out["reconnect"] += irr.reconnect_per_hour * hours
        out["burst"] += irr.burst_per_hour * hours
        out["wrong_password"] += irr.wrong_password_per_hour * hours
    return out


def rate_failures(
    observed: dict[str, int], expected: dict[str, float], tolerance: float
) -> list[str]:
    """Irregularity types whose observed count is outside expected ± tolerance."""
    return [
        f"{k}: observed {observed[k]}, expected {v:g} ± {tolerance:.0%}"
        for k, v in expected.items()
        if abs(observed[k] - v) > tolerance * v
    ]


# --- CLI ---------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m thesis.testbed.benign")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_plan = sub.add_parser("plan", help="write one plan per emulator into a run folder")
    p_plan.add_argument("profile", type=Path)
    p_plan.add_argument("out_dir", type=Path)
    p_plan.add_argument("--seed", type=int)
    p_plan.add_argument("--duration-s", type=int)
    p_count = sub.add_parser("count", help="compare a run's irregularity counts with the profile")
    p_count.add_argument("run_dir", type=Path)
    p_count.add_argument("--duration-s", type=int, required=True)
    p_count.add_argument("--profile", type=Path, default=PROFILE_PATH)
    p_cmp = sub.add_parser("compare", help="check two runs have identical message sequences")
    p_cmp.add_argument("run_a", type=Path)
    p_cmp.add_argument("run_b", type=Path)
    args = parser.parse_args(argv)

    if args.cmd == "plan":
        write_plans(args.profile, args.out_dir, args.seed, args.duration_s)
        return 0
    if args.cmd == "count":
        profile = load_profile(args.profile)
        observed = observed_counts(args.run_dir)
        expected = expected_counts(profile, args.duration_s)
        print(json.dumps({"observed": observed, "expected": expected}, sort_keys=True))
        failures = rate_failures(observed, expected, profile.tolerance)
        for f in failures:
            print(f"OUT OF TOLERANCE {f}", file=sys.stderr)
        return 1 if failures else 0
    a = message_sequences(parse_mqtt_log(args.run_a / "mqtt" / "mqtt.log"))
    b = message_sequences(parse_mqtt_log(args.run_b / "mqtt" / "mqtt.log"))
    print(json.dumps({d: len(s) for d, s in a.items()}, sort_keys=True))
    return 0 if a == b else 1


if __name__ == "__main__":
    raise SystemExit(main())
