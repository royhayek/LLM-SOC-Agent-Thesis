"""Generate the corpus schedule for the frozen target N (E2-03, SCRUM-32).

A seeded, deterministic generator turns the frozen targets (`config/corpus.yaml`, from the power
calculation METHODS.md v1.1 and the split E2-01) into one validated schedule:

    python -m thesis.scenario.generate

It writes `schedules/corpus-v1.0.0.yaml` and `docs/corpus/expected_counts.md`. Run twice with the
same `schedules/corpus.seed`, both outputs are byte-identical. The schedule is the ground truth
(record §4.1); a seeded script, not a hand-edited file, is what makes the corpus reproducible.

Bundle counting assumes 60 s tiling per device (record §4.1): a 60 s-aligned episode of duration
d covers exactly d / 60 windows, and each benign-block window yields one benign bundle per
continuously-publishing MQTT device (E1-05). Empty windows are dropped at assembly (E3-05), so the
benign target carries a margin.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from thesis.scenario.schedule import AttackFamily, BenignPeriod, Episode, Schedule, Split

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = REPO_ROOT / "schedules" / "corpus.seed"
CONFIG_PATH = REPO_ROOT / "config" / "corpus.yaml"
SCHEDULE_PATH = REPO_ROOT / "schedules" / "corpus-v1.0.0.yaml"
COUNTS_PATH = REPO_ROOT / "docs" / "corpus" / "expected_counts.md"

_FAMILY_ABBREV = {
    "ssh_brute_force": "ssh",
    "port_scan": "scan",
    "mqtt_publish_flood": "mflood",
    "mqtt_brute_force": "mbrute",
    "syn_flood": "syn",
    "botnet": "bot",
}
_MAX_BENIGN_WINDOWS = 10  # cap a single benign block at 10 windows (600 s) for readability


@dataclass(frozen=True)
class _RawEpisode:
    family: str
    device: str
    duration_s: int
    split: Split
    seed: int


@dataclass
class Report:
    """Expected counts computed from the schedule geometry."""

    window_s: int
    family_eval: dict[str, int] = field(default_factory=dict)
    family_train: dict[str, int] = field(default_factory=dict)
    benign_eval: int = 0
    benign_train: int = 0
    eval_target: int = 0
    benign_target: int = 0
    wall_clock_s: int = 0


def _read_seed() -> int:
    return int(SEED_PATH.read_text(encoding="utf-8").strip())


def _read_config() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return data


def _train_target(eval_target: int, train_share: float) -> int:
    return math.ceil(eval_target * train_share / (1.0 - train_share))


def _generate_raw_episodes(config: dict[str, Any], rng: random.Random) -> list[_RawEpisode]:
    """One pass per family: draw eval episodes until the eval bundle target is met, then train
    episodes until the train target is met. The split is decided here, from the seed, before any
    attack runs (E2-01). Device is round-robin over the family's eligible devices."""
    window_s: int = config["window_seconds"]
    durations: list[int] = config["episode_durations_s"]
    eval_target: int = config["eval_bundles_per_family"]
    train_target = _train_target(eval_target, config["train_share"])
    device_map: dict[str, list[str]] = config["devices"]

    raws: list[_RawEpisode] = []
    for family in config["families"]:
        eligible = device_map[family]
        rr = 0
        for split, target in ((Split.EVAL, eval_target), (Split.TRAIN, train_target)):
            bundles = 0
            while bundles < target:
                duration = rng.choice(durations)
                device = eligible[rr % len(eligible)]
                rr += 1
                raws.append(
                    _RawEpisode(family, device, duration, split, rng.randrange(1, 1_000_000))
                )
                bundles += duration // window_s
    return raws


def _lay_out_episodes(raws: list[_RawEpisode], gap_s: int) -> tuple[list[Episode], int]:
    """Place each device's episodes back to back with a gap, 60 s aligned, so none overlap on one
    device (record §4.1). Returns the episodes and the last end offset across all devices."""
    per_family_index: dict[str, int] = {}
    next_start: dict[str, int] = {}
    episodes: list[Episode] = []
    for raw in raws:
        n = per_family_index.get(raw.family, 0) + 1
        per_family_index[raw.family] = n
        start = next_start.get(raw.device, 0)
        next_start[raw.device] = start + raw.duration_s + gap_s
        episodes.append(
            Episode(
                id=f"ep-{_FAMILY_ABBREV[raw.family]}-{raw.split.value}-{n:03d}",
                family=AttackFamily(raw.family),
                target_device=raw.device,
                start_offset_s=start,
                duration_s=raw.duration_s,
                parameters={},
                seed=raw.seed,
                split=raw.split,
            )
        )
    last_end = max((e.end_offset_s for e in episodes), default=0)
    return episodes, last_end


def _build_benign(
    config: dict[str, Any], start_at: int
) -> tuple[list[BenignPeriod], int, int, int]:
    """Benign blocks after the attack phase, each tagged with its split. Sized so every split
    clears its bundle target with margin, counting one bundle per window per MQTT device."""
    window_s: int = config["window_seconds"]
    n_mqtt = len(config["mqtt_devices"])
    margin: float = config["benign_margin"]
    eval_target: int = config["benign_eval_bundles"]
    train_target = _train_target(eval_target, config["train_share"])

    periods: list[BenignPeriod] = []
    offset = start_at
    eval_bundles = train_bundles = 0
    for split, target in ((Split.EVAL, eval_target), (Split.TRAIN, train_target)):
        needed_windows = math.ceil(target * (1.0 + margin) / n_mqtt)
        n = 0
        while needed_windows > 0:
            w = min(_MAX_BENIGN_WINDOWS, needed_windows)
            needed_windows -= w
            n += 1
            periods.append(
                BenignPeriod(
                    id=f"bn-{split.value}-{n:03d}",
                    start_offset_s=offset,
                    duration_s=w * window_s,
                    split=split,
                )
            )
            offset += w * window_s
            if split is Split.EVAL:
                eval_bundles += w * n_mqtt
            else:
                train_bundles += w * n_mqtt
    return periods, eval_bundles, train_bundles, offset


def build_schedule(config: dict[str, Any], seed: int) -> tuple[Schedule, Report]:
    rng = random.Random(seed)
    window_s: int = config["window_seconds"]
    raws = _generate_raw_episodes(config, rng)
    episodes, attack_end = _lay_out_episodes(raws, config["gap_s"])
    benign, benign_eval, benign_train, wall_clock = _build_benign(config, attack_end)

    schedule = Schedule(episodes=tuple(episodes), benign_periods=tuple(benign))

    report = Report(
        window_s=window_s,
        eval_target=config["eval_bundles_per_family"],
        benign_target=config["benign_eval_bundles"],
        benign_eval=benign_eval,
        benign_train=benign_train,
        wall_clock_s=wall_clock,
    )
    for e in episodes:
        bundles = e.duration_s // window_s
        bucket = report.family_eval if e.split is Split.EVAL else report.family_train
        bucket[e.family.value] = bucket.get(e.family.value, 0) + bundles
    return schedule, report


def _dump_schedule(schedule: Schedule) -> str:
    data = schedule.model_dump(mode="json")
    header = (
        "# Corpus schedule v1.0.0 (E2-03, SCRUM-32). GENERATED by `python -m thesis.scenario.\n"
        "# generate` from config/corpus.yaml and schedules/corpus.seed. Do not edit by hand:\n"
        "# edit the config or the seed and regenerate. Every episode carries a `split` (E2-01).\n"
    )
    body: str = yaml.safe_dump(data, sort_keys=True, default_flow_style=False, allow_unicode=True)
    return header + body


def _render_counts_md(report: Report, config: dict[str, Any], seed: int) -> str:
    train_target = _train_target(report.eval_target, config["train_share"])
    benign_train_target = _train_target(report.benign_target, config["train_share"])
    families = list(config["families"])

    lines = [
        "# Corpus v1.0.0 expected counts (E2-03, SCRUM-32)",
        "",
        "GENERATED by `python -m thesis.scenario.generate` from `config/corpus.yaml` and",
        f"`schedules/corpus.seed` (seed `{seed}`). Do not edit by hand; regenerate instead.",
        "",
        "Expected bundle counts assume 60 s tiling per device (record §4.1): a 60 s-aligned",
        "episode of duration d covers exactly d / 60 windows, and each benign-block window yields",
        "one benign bundle per MQTT device (E1-05). Targets are from the power calculation",
        f"(METHODS.md v1.1, E2-02): {report.eval_target} evaluation bundles per family and",
        f"{report.benign_target} benign; the per-family H1 floor is 30 (power_calculation.md §5).",
        "The split is E2-01 (70 / 30 eval / train, seeded before generation).",
        "",
        "## Attack bundles per family",
        "",
        "| Family | Eval (target ≥ "
        + f"{report.eval_target}) | Train (target ≥ {train_target}) | Total |",
        "|---|---|---|---|",
    ]
    total_eval = total_train = 0
    for fam in families:
        ev = report.family_eval.get(fam, 0)
        tr = report.family_train.get(fam, 0)
        total_eval += ev
        total_train += tr
        lines.append(f"| {fam} | {ev} | {tr} | {ev + tr} |")
    lines.append(
        f"| **All six** | **{total_eval}** | **{total_train}** | **{total_eval + total_train}** |"
    )

    hours = report.wall_clock_s / 3600.0
    lines += [
        "",
        "## Benign bundles",
        "",
        "| Split | Expected | Target |",
        "|---|---|---|",
        f"| eval | {report.benign_eval} | {report.benign_target} |",
        f"| train | {report.benign_train} | {benign_train_target} |",
        "",
        f"Benign bundles are counted only from the explicit benign blocks, across the "
        f"{len(config['mqtt_devices'])} MQTT emulators that publish continuously. Idle",
        "device-windows during the attack phase (gaps between episodes, and the IoT devices while",
        "the honeypot families run) yield further benign bundles that are not counted here, so the",
        "benign floor holds with margin even after empty windows are dropped at assembly (E3-05).",
        "",
        "## Totals and wall-clock",
        "",
        f"- Evaluation bundles: {total_eval} attack + {report.benign_eval} benign = "
        f"{total_eval + report.benign_eval} (target N_eval = "
        f"{report.eval_target * len(families) + report.benign_target}).",
        f"- Training bundles: {total_train} attack + {report.benign_train} benign = "
        f"{total_train + report.benign_train}.",
        f"- **Total wall-clock of the schedule: {report.wall_clock_s} s "
        f"(~{hours:.1f} h).** Plan the corpus run (E2-05) for a night; E2-05 checks the real time.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    seed = _read_seed()
    config = _read_config()
    schedule, report = build_schedule(config, seed)
    # Validate against the E1-06 contract before writing (no same-device overlap, unique ids).
    Schedule.model_validate(schedule.model_dump(mode="json"))

    SCHEDULE_PATH.write_text(_dump_schedule(schedule), encoding="utf-8")
    COUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COUNTS_PATH.write_text(_render_counts_md(report, config, seed), encoding="utf-8")

    n_attack = len(schedule.episodes)
    n_benign = len(schedule.benign_periods)
    sched = SCHEDULE_PATH.relative_to(REPO_ROOT)
    counts = COUNTS_PATH.relative_to(REPO_ROOT)
    print(f"wrote {sched}: {n_attack} episodes, {n_benign} benign blocks")
    print(f"wrote {counts}; wall-clock ~{report.wall_clock_s / 3600.0:.1f} h")


if __name__ == "__main__":
    main()
