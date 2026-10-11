"""Tests for the corpus chunker (E2-05, SCRUM-52).

The corpus is the instrument, so the one thing that must never happen is a chunking bug that
drops, duplicates or mutates an episode. These tests pin that down on the real corpus schedule.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from thesis.scenario.chunk import chunk_schedule
from thesis.scenario.schedule import Episode, Schedule, load_schedule

CORPUS = Path(__file__).resolve().parent.parent / "schedules" / "corpus-v1.0.0.yaml"


def _corpus() -> Schedule:
    return load_schedule(CORPUS)


def test_every_episode_appears_exactly_once() -> None:
    s = _corpus()
    chunks = chunk_schedule(s, 6)
    got = sorted(e.id for c in chunks for e in c.episodes)
    assert got == sorted(e.id for e in s.episodes)
    assert len(got) == len(set(got)), "an episode was duplicated across chunks"


def test_every_benign_block_appears_exactly_once() -> None:
    s = _corpus()
    chunks = chunk_schedule(s, 6)
    got = sorted(b.id for c in chunks for b in c.benign_periods)
    assert got == sorted(b.id for b in s.benign_periods)


def test_episode_fields_are_preserved_only_offset_changes() -> None:
    s = _corpus()
    master: dict[str, Episode] = {e.id: e for e in s.episodes}
    for c in chunk_schedule(s, 6):
        for e in c.episodes:
            m = master[e.id]
            assert (e.family, e.target_device, e.duration_s, e.seed, e.split) == (
                m.family,
                m.target_device,
                m.duration_s,
                m.seed,
                m.split,
            )


def test_each_chunk_is_a_valid_schedule() -> None:
    # Schedule construction runs the E1-06 validators; round-trip to be sure.
    for c in chunk_schedule(_corpus(), 6):
        Schedule.model_validate(c.model_dump(mode="json"))


def test_chunking_is_deterministic() -> None:
    s = _corpus()
    a = [c.model_dump(mode="json") for c in chunk_schedule(s, 6)]
    b = [c.model_dump(mode="json") for c in chunk_schedule(s, 6)]
    assert a == b


def test_n_chunks_must_be_positive() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        chunk_schedule(_corpus(), 0)


def test_one_chunk_returns_all_items() -> None:
    s = _corpus()
    (only,) = chunk_schedule(s, 1)
    assert len(only.episodes) == len(s.episodes)
    assert len(only.benign_periods) == len(s.benign_periods)
