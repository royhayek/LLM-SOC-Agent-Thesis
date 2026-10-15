"""The episode-level block bootstrap (E9-06, SCRUM-93).

Bundles from one attack episode are not independent: a four-minute flood yields several
positively-labelled bundles that move together (record §4.1). A bundle-level bootstrap would treat
them as independent and overstate precision. The fix frozen in METHODS.md §4.3 is to resample whole
episodes: **the episode is the resampling unit**, and a benign bundle forms a block of its own,
because benign traffic has no episode structure in the schedule.

The statistic is the per-bundle mean paired difference `D = (1/N) Σ_b d(b)` (safety_scoring §5): a
resample draws blocks with replacement, pools every bundle in the drawn blocks, and takes their
mean. The gotcha is to average the block means instead — that reweights small episodes and is not
the bundle-level statistic the hypotheses report. Both interval forms come from the same resample
distribution: the two-sided 95 % percentile interval for a §4.3 contrast, and the one-sided 95 %
lower bound for the H3 usefulness non-inferiority margin (safety_scoring §5, δ = 0.05).

B = 10,000 and the seed are fixed and logged (§4.3); this module changes no primary metric.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

B_DEFAULT = 10_000  # METHODS.md §4.3, frozen
ALPHA = 0.05


@dataclass(frozen=True)
class BootstrapCI:
    """A bootstrap confidence interval of the paired difference `D` (first condition − second)."""

    estimate: float  # observed D on the full sample (not a resample)
    lo: float  # two-sided lower bound, the alpha/2 percentile (§4.3 contrasts)
    hi: float  # two-sided upper bound, the 1 − alpha/2 percentile
    lower_one_sided: float  # one-sided lower bound, the alpha percentile (H3 non-inferiority)
    b: int
    seed: int

    @property
    def excludes_zero(self) -> bool:
        """§4.3: a contrast is robust to clustering only if the two-sided interval excludes 0."""
        return self.lo > 0.0 or self.hi < 0.0


def _pooled_mean(blocks: Sequence[Sequence[float]]) -> float:
    total = 0.0
    count = 0
    for block in blocks:
        for value in block:
            total += value
            count += 1
    return total / count if count else 0.0


def block_bootstrap_ci(
    blocks: Sequence[Sequence[float]],
    *,
    seed: int,
    b: int = B_DEFAULT,
    alpha: float = ALPHA,
) -> BootstrapCI:
    """Resample whole blocks (episodes) with replacement and return the interval of the bundle-mean.

    `blocks` is one sequence of per-bundle values per block; an attack episode is one block and each
    benign bundle is a block of its own (§4.3). The estimate and both interval forms are computed
    from `b` resamples of the block indices, seeded for exact reproducibility.
    """
    n_blocks = len(blocks)
    if n_blocks == 0:
        return BootstrapCI(0.0, 0.0, 0.0, 0.0, b, seed)

    # Flat value array plus each block's slice, so a resample only re-sums, never re-iterates.
    flat: list[float] = []
    bounds: list[tuple[int, int]] = []
    for block in blocks:
        start = len(flat)
        flat.extend(block)
        bounds.append((start, len(flat)))
    values = np.asarray(flat, dtype=np.float64)
    sums = np.array([values[s:e].sum() for s, e in bounds])
    sizes = np.array([e - s for s, e in bounds], dtype=np.float64)

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_blocks, size=(b, n_blocks))  # draw block indices with replacement
    resample_sum = sums[idx].sum(axis=1)
    resample_size = sizes[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        means = np.where(resample_size > 0, resample_sum / resample_size, 0.0)

    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    lower_one_sided = float(np.percentile(means, 100 * alpha))
    return BootstrapCI(
        estimate=_pooled_mean(blocks),
        lo=float(lo),
        hi=float(hi),
        lower_one_sided=lower_one_sided,
        b=b,
        seed=seed,
    )


def blocks_from_episodes(episode_ids: Iterable[str], values: Iterable[float]) -> list[list[float]]:
    """Group per-bundle `values` into blocks by episode id. A benign bundle (`episode_id == ""`)
    becomes its own singleton block (§4.3); attack bundles sharing an episode join one block.

    Episode order is the first-seen order, so the block list is deterministic for a fixed seed.
    """
    attack: dict[str, list[float]] = defaultdict(list)
    order: list[str] = []
    benign: list[list[float]] = []
    for episode_id, value in zip(episode_ids, values, strict=True):
        if episode_id == "":
            benign.append([value])
            continue
        if episode_id not in attack:
            order.append(episode_id)
        attack[episode_id].append(value)
    return [attack[e] for e in order] + benign


def paired_difference_blocks(
    rows_a: Iterable[Mapping[str, object]],
    rows_b: Iterable[Mapping[str, object]],
    score: object,
    *,
    episode_of: Mapping[str, str],
) -> list[list[float]]:
    """Build the per-episode blocks of the paired difference `d(b) = score_a(b) − score_b(b)`.

    `score` maps a per-bundle list of rows to a scalar (for example the mean USE over repetitions);
    `episode_of` maps a bundle id to its episode id (`""` for benign). Only bundles scored under
    both conditions contribute, so the pairing stays exact (§4.2).
    """
    by_bundle_a = _by_bundle(rows_a)
    by_bundle_b = _by_bundle(rows_b)
    bundles = sorted(set(by_bundle_a) & set(by_bundle_b))
    diffs = [float(score(by_bundle_a[x])) - float(score(by_bundle_b[x])) for x in bundles]  # type: ignore[operator]
    episodes = [episode_of.get(x, "") for x in bundles]
    return blocks_from_episodes(episodes, diffs)


def _by_bundle(rows: Iterable[Mapping[str, object]]) -> dict[str, list[Mapping[str, object]]]:
    groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["bundle_id"])].append(row)
    return groups


__all__ = [
    "BootstrapCI",
    "block_bootstrap_ci",
    "blocks_from_episodes",
    "paired_difference_blocks",
]
