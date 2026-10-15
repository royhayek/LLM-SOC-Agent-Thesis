"""The paired hypothesis tests H1–H4 (E9-05, SCRUM-84).

Every hypothesis claims "significantly"; the comparisons are paired because every condition sees the
same bundles (proposal Methodology). The tests and the correction were frozen in METHODS.md §4.2
before any result existed, and are listed here exactly — one row per frozen comparison and no
other, so a comparison cannot be added after seeing results (the gotcha).

- Binary outcomes (DET, CLS): the bundle's outcome is the **majority over its k repetitions** on
  the emitted verdict (§3.2); paired conditions are compared with **McNemar** (exact binomial when
  the discordant pairs number fewer than 25, else the continuity-corrected chi-square).
- The contextually-unsafe rate CU: the **per-bundle mean over repetitions**, compared with the
  **Wilcoxon signed-rank** test.
- Within each Holm family (H1: 6, H4: 6, H2: 1, H3: 1) the p-values are Holm-adjusted; the H3
  usefulness non-inferiority test is a bootstrap outside the families (E9-06).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from scipy import stats  # type: ignore[import-untyped]

from thesis.config import ExperimentConfig, config_hash
from thesis.eval.metrics import BENIGN, _action_sets, _pred, _truth, map_action

# The frozen comparisons (METHODS.md §4.2), by condition label. C1 full agent; C2–C4 single source;
# C5 safety off; C6 Baseline B; C7 Baseline A (config/conditions.yaml order C1..C7).
C_INDEX = {"C1": 0, "C2": 1, "C3": 2, "C4": 3, "C5": 4, "C6": 5, "C7": 6}


@dataclass(frozen=True)
class Comparison:
    hypothesis: str
    family: str  # Holm family key; "" means outside any family
    a: str  # condition label
    b: str
    outcome: str  # DET | CLS | CU
    test: str  # mcnemar | wilcoxon


COMPARISONS: list[Comparison] = [
    # H1: all sources beat each single source, on DET and CLS (Holm family of 6)
    *(
        Comparison("H1", "H1", "C1", c, o, "mcnemar")
        for c in ("C2", "C3", "C4")
        for o in ("DET", "CLS")
    ),
    # H2: agentic beats prompt-only, on CLS (family of 1)
    Comparison("H2", "H2", "C5", "C6", "CLS", "mcnemar"),
    # H3: safety cuts the unsafe rate, on CU (family of 1; usefulness non-inferiority is E9-06)
    Comparison("H3", "H3", "C1", "C5", "CU", "wilcoxon"),
    # H4: the agent beats both baselines, on DET, CLS and CU (Holm family of 6)
    *(
        Comparison("H4", "H4", "C1", b, o, "mcnemar" if o != "CU" else "wilcoxon")
        for b in ("C7", "C6")
        for o in ("DET", "CLS", "CU")
    ),
]


def _by_condition(rows: Iterable[Mapping[str, object]]) -> dict[str, list[Mapping[str, object]]]:
    groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["config_hash"])].append(row)
    return groups


def _det_correct(row: Mapping[str, object]) -> bool:
    pred = _pred(row)
    truth_attack = _truth(row) != BENIGN
    if pred is None:
        return False  # unusable output is always wrong
    return (pred != BENIGN) == truth_attack


def _cls_correct(row: Mapping[str, object]) -> bool:
    return _pred(row) == _truth(row)


def _cu(row: Mapping[str, object], unsafe: dict[str, set[str]]) -> float:
    action = map_action(
        None if row.get("recommended_action") is None else str(row["recommended_action"])
    )
    return 1.0 if action in unsafe.get(_truth(row), set()) else 0.0


def _per_bundle_binary(rows: list[Mapping[str, object]], correct: object) -> dict[str, bool]:
    """Majority-over-repetitions correctness per bundle for one condition."""
    by_bundle: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        by_bundle[str(row["bundle_id"])].append(bool(correct(row)))  # type: ignore[operator]
    return {b: sum(vals) > len(vals) / 2 for b, vals in by_bundle.items()}


def _per_bundle_mean_cu(
    rows: list[Mapping[str, object]], unsafe: dict[str, set[str]]
) -> dict[str, float]:
    by_bundle: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_bundle[str(row["bundle_id"])].append(_cu(row, unsafe))
    return {b: sum(vals) / len(vals) for b, vals in by_bundle.items()}


def mcnemar(a: list[bool], b: list[bool]) -> tuple[float, float]:
    """Paired McNemar. Returns (continuity-corrected chi-square, p-value). Exact binomial p when the
    discordant pairs number < 25 (§3.2), else the chi-square p-value."""
    b01 = sum(1 for x, y in zip(a, b, strict=True) if not x and y)
    b10 = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    n = b01 + b10
    if n == 0:
        return 0.0, 1.0
    chi2 = (abs(b01 - b10) - 1) ** 2 / n
    if n < 25:
        p = float(stats.binomtest(min(b01, b10), n, 0.5, alternative="two-sided").pvalue)
    else:
        p = float(stats.chi2.sf(chi2, df=1))
    return chi2, p


def wilcoxon(a: list[float], b: list[float]) -> tuple[float, float]:
    """Paired Wilcoxon signed-rank on the per-bundle scores. Returns (statistic, p-value)."""
    diffs = [x - y for x, y in zip(a, b, strict=True)]
    if not any(diffs):
        return 0.0, 1.0
    result = stats.wilcoxon(a, b)
    return float(result.statistic), float(result.pvalue)


def holm(pvalues: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[idx]))
        adjusted[idx] = running
    return adjusted


@dataclass(frozen=True)
class TestResult:
    hypothesis: str
    contrast: str
    outcome: str
    test: str
    statistic: float
    p_value: float
    p_holm: float
    effect: float  # mean per-bundle difference a − b (positive favours the first condition)


def run_tests(
    rows: Iterable[Mapping[str, object]], conditions: list[ExperimentConfig]
) -> list[TestResult]:
    """Run every frozen comparison (and only those); Holm-adjust within each family."""
    hashes = {label: config_hash(conditions[idx]) for label, idx in C_INDEX.items()}
    groups = _by_condition(rows)
    _, unsafe = _action_sets()

    raw: list[tuple[Comparison, float, float, float]] = []
    for cmp in COMPARISONS:
        ga, gb = groups.get(hashes[cmp.a], []), groups.get(hashes[cmp.b], [])
        if cmp.test == "mcnemar":
            correct = _det_correct if cmp.outcome == "DET" else _cls_correct
            pa, pb = _per_bundle_binary(ga, correct), _per_bundle_binary(gb, correct)
            bundles = sorted(set(pa) & set(pb))
            va, vb = [pa[x] for x in bundles], [pb[x] for x in bundles]
            stat, p = mcnemar(va, vb)
            effect = (sum(va) - sum(vb)) / len(bundles) if bundles else 0.0
        else:  # wilcoxon on per-bundle mean CU
            pa_cu, pb_cu = _per_bundle_mean_cu(ga, unsafe), _per_bundle_mean_cu(gb, unsafe)
            bundles = sorted(set(pa_cu) & set(pb_cu))
            fa, fb = [pa_cu[x] for x in bundles], [pb_cu[x] for x in bundles]
            stat, p = wilcoxon(fa, fb)
            effect = (sum(fa) - sum(fb)) / len(bundles) if bundles else 0.0
        raw.append((cmp, stat, p, effect))

    adjusted: dict[str, list[float]] = {}
    for family in {c.family for c in COMPARISONS}:
        idxs = [i for i, (cmp, *_rest) in enumerate(raw) if cmp.family == family]
        fam_p = holm([raw[i][2] for i in idxs])
        for i, adj in zip(idxs, fam_p, strict=True):
            adjusted[str(i)] = [adj]

    results = []
    for i, (cmp, stat, p, effect) in enumerate(raw):
        results.append(
            TestResult(
                hypothesis=cmp.hypothesis,
                contrast=f"{cmp.a} vs {cmp.b}",
                outcome=cmp.outcome,
                test=cmp.test,
                statistic=round(stat, 4),
                p_value=round(p, 4),
                p_holm=round(adjusted[str(i)][0], 4),
                effect=round(effect, 4),
            )
        )
    return results


__all__ = ["COMPARISONS", "TestResult", "holm", "mcnemar", "run_tests", "wilcoxon"]
