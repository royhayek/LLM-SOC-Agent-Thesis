"""Tests for the frozen-bundle-set split logic (E3-09, SCRUM-105).

Pure logic only — the split rule and benign-block overlap. The end-to-end build runs on the
git-ignored corpus, so it is exercised by `python -m thesis.assemble.build_frozen`, not in CI.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from thesis.assemble.build_frozen import (
    EVAL,
    TRAIN,
    _attack_split,
    _benign_split,
    _overlap_s,
)
from thesis.assemble.bundles import Bundle

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _bundle(device: str, offset: int) -> Bundle:
    ws = T0 + timedelta(seconds=offset)
    return Bundle(
        bundle_id=f"{device}|{ws.isoformat()}",
        device=device,
        window_start=ws,
        window_end=ws + timedelta(seconds=60),
        label="benign",
        episode_id=None,
        sources=("mqtt",),
        alerts=(),
    )


def test_attack_split_reads_the_episode_id() -> None:
    assert _attack_split("ep-ssh-eval-001") == EVAL
    assert _attack_split("ep-bot-train-042") == TRAIN
    assert _attack_split(None) == EVAL  # no episode id defaults to eval, never silently train


def test_overlap_seconds() -> None:
    a, b = T0, T0 + timedelta(seconds=100)
    assert _overlap_s(a, a + timedelta(seconds=60), a, b) == 60.0
    assert _overlap_s(b, b + timedelta(seconds=60), a, b) == 0.0  # touching, half-open


def test_benign_split_picks_the_most_overlapping_block() -> None:
    blocks = [
        (T0, T0 + timedelta(seconds=600), EVAL),
        (T0 + timedelta(seconds=600), T0 + timedelta(seconds=1200), TRAIN),
    ]
    mqtt = {"iot-temp-01"}
    assert _benign_split(_bundle("iot-temp-01", 120), blocks, mqtt) == EVAL
    assert _benign_split(_bundle("iot-temp-01", 660), blocks, mqtt) == TRAIN
    # Outside every block -> not counted (the uncounted idle-phase margin).
    assert _benign_split(_bundle("iot-temp-01", 5000), blocks, mqtt) is None
    # Not an MQTT device -> never a counted benign bundle.
    assert _benign_split(_bundle("hp-ssh-01", 120), blocks, mqtt) is None
