"""Tests for the episode-level block bootstrap (E9-06, SCRUM-93)."""

from __future__ import annotations

import numpy as np
import pytest

from thesis.eval.bootstrap import (
    block_bootstrap_ci,
    blocks_from_episodes,
    paired_difference_blocks,
)

SEED = 20260615


def test_singleton_blocks_match_an_ordinary_bootstrap_within_0_01() -> None:
    """AC1: when every episode has exactly one bundle, the block bootstrap reduces to resampling
    the bundles directly, so its interval matches an ordinary bundle bootstrap."""
    rng = np.random.default_rng(1)
    diffs = rng.normal(0.2, 1.0, size=80).tolist()

    singleton_blocks = [[d] for d in diffs]  # one bundle per episode
    block_ci = block_bootstrap_ci(singleton_blocks, seed=SEED)

    # Ordinary bootstrap: resample the bundle values themselves, same seed and draw shape.
    values = np.asarray(diffs)
    gen = np.random.default_rng(SEED)
    idx = gen.integers(0, len(values), size=(10_000, len(values)))
    means = values[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])

    assert block_ci.lo == pytest.approx(float(lo), abs=0.01)
    assert block_ci.hi == pytest.approx(float(hi), abs=0.01)


def test_same_seed_gives_identical_intervals() -> None:
    """AC2: two runs with the same seed produce bit-for-bit identical intervals."""
    blocks = [[0.1, 0.2, 0.0, 0.3], [0.4], [-0.1, -0.2], [0.5, 0.5, 0.5]]
    first = block_bootstrap_ci(blocks, seed=SEED)
    second = block_bootstrap_ci(blocks, seed=SEED)
    assert (first.lo, first.hi, first.lower_one_sided, first.estimate) == (
        second.lo,
        second.hi,
        second.lower_one_sided,
        second.estimate,
    )
    # A different seed moves the interval (sanity: the seed is actually used). Needs enough blocks
    # that the percentile is not pinned to one discrete value.
    many = [[v] for v in np.random.default_rng(3).normal(0.1, 1.0, size=60).tolist()]
    assert block_bootstrap_ci(many, seed=SEED).lo != block_bootstrap_ci(many, seed=SEED + 1).lo


def test_estimate_is_the_pooled_bundle_mean_not_the_block_mean() -> None:
    # One 3-bundle episode of 0.0 and one 1-bundle episode of 0.9.
    # Bundle mean = (0+0+0+0.9)/4 = 0.225; averaging block means would give (0.0+0.9)/2 = 0.45.
    ci = block_bootstrap_ci([[0.0, 0.0, 0.0], [0.9]], seed=SEED)
    assert ci.estimate == pytest.approx(0.225)


def test_clustering_widens_the_interval_versus_independent_bundles() -> None:
    # Four episodes of four perfectly-correlated bundles each carry less information than sixteen
    # independent bundles, so the clustered interval must be wider.
    clustered = [[0.5] * 4, [-0.5] * 4, [0.5] * 4, [-0.5] * 4]
    independent = [[v] for block in clustered for v in block]
    wide = block_bootstrap_ci(clustered, seed=SEED)
    narrow = block_bootstrap_ci(independent, seed=SEED)
    assert (wide.hi - wide.lo) > (narrow.hi - narrow.lo)


def test_one_sided_lower_bound_is_above_the_two_sided_lower_bound() -> None:
    rng = np.random.default_rng(2)
    blocks = [rng.normal(0.1, 0.5, size=4).tolist() for _ in range(40)]
    ci = block_bootstrap_ci(blocks, seed=SEED)
    assert ci.lower_one_sided >= ci.lo  # 5th percentile is at or above the 2.5th


def test_excludes_zero_flags_a_robust_contrast() -> None:
    positive = block_bootstrap_ci([[1.0, 1.0], [1.0], [1.0, 1.0, 1.0]], seed=SEED)
    assert positive.excludes_zero  # all differences positive -> interval well above 0
    straddling = block_bootstrap_ci([[1.0], [-1.0], [1.0], [-1.0]], seed=SEED)
    assert not straddling.excludes_zero


def test_blocks_from_episodes_groups_attacks_and_isolates_benign() -> None:
    episodes = ["ep1", "ep1", "", "ep2", "", "ep1"]
    values = [0.1, 0.2, 0.9, 0.3, 0.8, 0.4]
    blocks = blocks_from_episodes(episodes, values)
    assert blocks == [[0.1, 0.2, 0.4], [0.3], [0.9], [0.8]]  # ep1, ep2, then each benign alone


def test_paired_difference_blocks_pairs_on_shared_bundles() -> None:
    rows_a = [{"bundle_id": "b1", "u": 1.0}, {"bundle_id": "b2", "u": 0.0}]
    rows_b = [{"bundle_id": "b1", "u": 1.0}, {"bundle_id": "b2", "u": 1.0}]
    blocks = paired_difference_blocks(
        rows_a,
        rows_b,
        lambda rs: sum(float(r["u"]) for r in rs) / len(rs),
        episode_of={"b1": "ep1", "b2": ""},
    )
    # b1: 1.0 − 1.0 = 0.0 (episode ep1); b2: 0.0 − 1.0 = −1.0 (benign, its own block).
    assert blocks == [[0.0], [-1.0]]


def test_empty_input_is_a_degenerate_zero_interval() -> None:
    ci = block_bootstrap_ci([], seed=SEED)
    assert (ci.lo, ci.hi, ci.estimate) == (0.0, 0.0, 0.0)
