"""Tests for mechanical window labelling (E2-04). These test the file and the pure function."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

import pytest

from thesis.labels import windows as win
from thesis.labels.windows import (
    BENIGN,
    ExecutedEpisode,
    LabelConflictError,
    WindowLabel,
    label_windows,
    load_window_seconds,
    read_executed_episodes,
)

T0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
W = 60
DEV = "iot-temp-01"


def _at(sec: int) -> datetime:
    return T0 + timedelta(seconds=sec)


def _ep(
    start: int, end: int, family: str = "ssh_brute_force", device: str = DEV, id_: str = "ep-1"
) -> ExecutedEpisode:
    return ExecutedEpisode(id=id_, family=family, device=device, start=_at(start), end=_at(end))


def _labels(
    episodes: list[ExecutedEpisode], end: int, devices: list[str] | None = None
) -> list[WindowLabel]:
    return label_windows(episodes, T0, _at(end), devices or [DEV], W)


def test_window_seconds_from_config_is_60() -> None:
    assert load_window_seconds() == 60


def test_episode_inside_one_window_labels_that_window_and_leaves_neighbours_benign() -> None:
    # Episode [70, 110) sits inside window 1 ([60, 120)); windows 0 and 2 are benign.
    labels = _labels([_ep(70, 110)], end=180)
    assert [(lbl.label, lbl.episode_id) for lbl in labels] == [
        (BENIGN, None),
        ("ssh_brute_force", "ep-1"),
        (BENIGN, None),
    ]
    assert [lbl.window_start for lbl in labels] == [_at(0), _at(60), _at(120)]


def test_episode_starting_in_the_last_second_of_a_window_still_labels_it() -> None:
    # Episode [59, 65): overlaps window 0 ([0, 60)) by 1 s, and window 1 ([60, 120)) by 5 s.
    labels = _labels([_ep(59, 65)], end=180)
    assert labels[0].label == "ssh_brute_force"  # window 0 carries it (1 s overlap)
    assert labels[1].label == "ssh_brute_force"
    assert labels[2].label == BENIGN


def test_adjacent_non_overlapping_episodes_give_one_label_each() -> None:
    # Window-aligned adjacency: ep A [0, 60), ep B [60, 120) on the same device.
    a = _ep(0, 60, family="port_scan", id_="a")
    b = _ep(60, 120, family="syn_flood", id_="b")
    labels = _labels([a, b], end=120)
    assert [(lbl.label, lbl.episode_id) for lbl in labels] == [
        ("port_scan", "a"),
        ("syn_flood", "b"),
    ]


def test_device_with_no_episode_is_all_benign() -> None:
    labels = label_windows([_ep(70, 110, device="iot-temp-01")], T0, _at(180), ["iot-cam-01"], W)
    assert all(lbl.device == "iot-cam-01" for lbl in labels)
    assert all(lbl.label == BENIGN and lbl.episode_id is None for lbl in labels)


def test_episode_spanning_several_windows_labels_each_with_the_same_id() -> None:
    labels = _labels([_ep(30, 150, id_="long")], end=180)
    assert [lbl.label for lbl in labels] == [
        "ssh_brute_force",
        "ssh_brute_force",
        "ssh_brute_force",
    ]
    assert {lbl.episode_id for lbl in labels[:3]} == {"long"}


def test_two_distinct_episodes_in_one_window_raise() -> None:
    a = _ep(5, 15, family="port_scan", id_="a")
    b = _ep(40, 50, family="syn_flood", id_="b")  # same device, same window [0, 60)
    with pytest.raises(LabelConflictError, match="must not share a window"):
        _labels([a, b], end=60)


def test_half_open_end_does_not_label_the_touching_window() -> None:
    # Episode [0, 60): overlaps window 0 only, not window 1 ([60, 120)).
    labels = _labels([_ep(0, 60)], end=120)
    assert labels[0].label == "ssh_brute_force"
    assert labels[1].label == BENIGN


def test_naive_times_are_rejected() -> None:
    naive = datetime(2026, 1, 1)
    with pytest.raises(ValueError, match="timezone-aware"):
        label_windows([], naive, naive + timedelta(seconds=60), [DEV], W)


def test_benign_as_an_episode_family_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-family label"):
        _labels([_ep(0, 60, family="benign")], end=60)


def test_read_executed_episodes_uses_actual_times_and_skips_no_runner(tmp_path: object) -> None:
    import json
    from pathlib import Path

    rows = [
        {"event": "isolation_check", "result": "pass"},
        {
            "event": "episode",
            "id": "ep-a",
            "family": "port_scan",
            "target_device": "hp-ssh-01",
            "actual_start_utc": "2026-01-01T00:00:10+00:00",
            "actual_end_utc": "2026-01-01T00:00:40+00:00",
            "planned_start_utc": "2026-01-01T00:00:08+00:00",
            "planned_end_utc": "2026-01-01T00:00:38+00:00",
        },
        {
            "event": "episode",
            "id": "ep-b",
            "family": "botnet",
            "target_device": "iot-cam-01",
            "actual_start_utc": None,
            "actual_end_utc": None,
        },
        {"event": "run_status", "valid": True},
    ]
    log = Path(str(tmp_path)) / "execution_log.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    eps = read_executed_episodes(log)
    assert len(eps) == 1  # the no_runner episode (actual_start None) is skipped
    assert eps[0].id == "ep-a" and eps[0].device == "hp-ssh-01"
    assert eps[0].start == datetime(2026, 1, 1, 0, 0, 10, tzinfo=UTC)  # actual, not planned


def test_module_has_no_function_taking_a_label() -> None:
    """Ground truth comes only from the schedule: no function accepts a label (E2-04 AC)."""
    for name, fn in inspect.getmembers(win, inspect.isfunction):
        params = set(inspect.signature(fn).parameters)
        assert "label" not in params, f"{name} accepts a label"
