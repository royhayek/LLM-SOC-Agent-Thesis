"""Tests for the corpus schedule generator (E2-03, SCRUM-32).

These cover the code around the schedule: determinism, that every episode carries a split, that
the counts clear their frozen targets, and that the output validates under the E1-06 contract.
"""

from __future__ import annotations

import math

from thesis.scenario import generate
from thesis.scenario.schedule import Schedule, Split


def _config() -> dict[str, object]:
    return generate._read_config()


def test_runs_are_byte_identical() -> None:
    config, seed = _config(), generate._read_seed()
    first, _ = generate.build_schedule(config, seed)
    second, _ = generate.build_schedule(config, seed)
    assert generate._dump_schedule(first) == generate._dump_schedule(second)


def test_every_episode_and_benign_block_carries_a_split() -> None:
    schedule, _ = generate.build_schedule(_config(), generate._read_seed())
    assert all(e.split in (Split.TRAIN, Split.EVAL) for e in schedule.episodes)
    assert all(b.split in (Split.TRAIN, Split.EVAL) for b in schedule.benign_periods)


def test_attack_counts_clear_the_per_family_targets() -> None:
    config, seed = _config(), generate._read_seed()
    _, report = generate.build_schedule(config, seed)
    eval_target = config["eval_bundles_per_family"]
    train_target = generate._train_target(eval_target, config["train_share"])  # type: ignore[arg-type]
    for family in config["families"]:  # type: ignore[attr-defined]
        assert report.family_eval[family] >= eval_target
        assert report.family_train[family] >= train_target


def test_benign_counts_clear_the_targets_with_margin() -> None:
    config, seed = _config(), generate._read_seed()
    _, report = generate.build_schedule(config, seed)
    assert report.benign_eval >= config["benign_eval_bundles"]
    train_target = generate._train_target(config["benign_eval_bundles"], config["train_share"])  # type: ignore[arg-type]
    assert report.benign_train >= train_target


def test_total_evaluation_bundles_reach_n_eval() -> None:
    config, seed = _config(), generate._read_seed()
    _, report = generate.build_schedule(config, seed)
    attack_eval = sum(report.family_eval.values())
    n_eval_target = report.eval_target * len(config["families"]) + report.benign_target  # type: ignore[arg-type]
    assert attack_eval + report.benign_eval >= n_eval_target


def test_output_validates_under_the_e1_06_contract() -> None:
    schedule, _ = generate.build_schedule(_config(), generate._read_seed())
    # Round-trips through the validator: no same-device overlap, unique ids (raises otherwise).
    Schedule.model_validate(schedule.model_dump(mode="json"))


def test_episodes_are_sixty_second_aligned() -> None:
    schedule, _ = generate.build_schedule(_config(), generate._read_seed())
    for e in schedule.episodes:
        assert e.start_offset_s % 60 == 0
        assert e.duration_s % 60 == 0


def test_no_two_episodes_overlap_on_one_device() -> None:
    schedule, _ = generate.build_schedule(_config(), generate._read_seed())
    by_device: dict[str, list[tuple[int, int]]] = {}
    for e in schedule.episodes:
        by_device.setdefault(e.target_device, []).append((e.start_offset_s, e.end_offset_s))
    for spans in by_device.values():
        spans.sort()
        for (s1, e1), (s2, _e2) in zip(spans, spans[1:], strict=False):
            assert s2 >= e1, f"overlap: {(s1, e1)} and {(s2, _e2)}"


def test_train_target_matches_the_split_ratio() -> None:
    # 30 % training share -> train is 30/70 of eval, rounded up.
    assert generate._train_target(50, 0.30) == math.ceil(50 * 0.30 / 0.70)
    assert generate._train_target(180, 0.30) == math.ceil(180 * 0.30 / 0.70)
