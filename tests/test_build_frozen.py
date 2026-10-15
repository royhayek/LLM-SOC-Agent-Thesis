"""Tests for the frozen-bundle-set split logic (E3-09, SCRUM-105).

Pure logic only — the attack split rule and the seeded benign split. The end-to-end build runs on
the git-ignored corpus, so it is exercised by `python -m thesis.assemble.build_frozen`, not in CI.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from thesis.assemble.build_frozen import (
    BENIGN_EVAL_SHARE,
    EVAL,
    TRAIN,
    _attack_split,
    _benign_split,
)
from thesis.assemble.bundles import Bundle

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _benign_bundle(bundle_id: str) -> Bundle:
    return Bundle(
        bundle_id=bundle_id,
        device="iot-temp-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="benign",
        episode_id=None,
        sources=("mqtt",),
        alerts=(),
    )


def test_attack_split_reads_the_episode_id() -> None:
    assert _attack_split("ep-ssh-eval-001") == EVAL
    assert _attack_split("ep-bot-train-042") == TRAIN
    assert _attack_split(None) == EVAL  # no episode id defaults to eval, never silently train


def test_benign_split_is_deterministic() -> None:
    bid = "iot-temp-01|2026-01-01T00:05:00+00:00"
    assert _benign_split(_benign_bundle(bid)) == _benign_split(_benign_bundle(bid))
    assert _benign_split(_benign_bundle(bid)) in (EVAL, TRAIN)


def test_benign_split_is_roughly_seventy_thirty() -> None:
    ids = [f"iot-temp-01|2026-01-01T{h:02d}:{m:02d}:00+00:00" for h in range(10) for m in range(60)]
    splits = [_benign_split(_benign_bundle(bid)) for bid in ids]
    eval_share = splits.count(EVAL) / len(splits)
    # Seeded hash split: close to the 0.70 target over 600 ids, never all-or-nothing.
    assert abs(eval_share - BENIGN_EVAL_SHARE) < 0.06
