"""H1 stratified by attack family and source visibility (E9-10, SCRUM-115).

H1 claims the all-sources agent beats each single source on detection and classification. Reported
unstratified it can pass trivially, because some families leave no trace in some sources (record
§3.2, risk #4). This separates the **gain from fusion** from the **gain from simply having a
source**: per attack family, the detection recall and classification accuracy of C1 (all sources)
and each single-source condition (C2 flows, C3 mqtt, C4 honeypot), with episode-bootstrap intervals
(§4.3), plus C1 minus the best single source. It also reports H1 with and without honeypot-keyed
bundles (no benign traffic reaches the honeypot, §8, so it inflates detection), and reliability per
family.

Bundle level is primary (§4.1): a bundle's outcome is the majority over its k repetitions on the
emitted verdict. Everything reads from the hashed results (E9-09) and the frozen bundle manifest.

    python -m thesis.eval.h1    # writes results/h1_stratified.csv and docs/eval/h1_analysis.md
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from thesis.config import ExperimentConfig, config_hash
from thesis.eval.bootstrap import block_bootstrap_ci, blocks_from_episodes
from thesis.eval.metrics import BENIGN, LABELS, _pred, _truth
from thesis.eval.stats import mcnemar

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_BUNDLES = REPO_ROOT / "data" / "bundles" / "v1.0.0" / "eval.parquet"
RESULTS_PARQUET = REPO_ROOT / "results" / "results.parquet"
STRATIFIED_CSV = REPO_ROOT / "results" / "h1_stratified.csv"
ANALYSIS_MD = REPO_ROOT / "docs" / "eval" / "h1_analysis.md"

FAMILIES = [label for label in LABELS if label != BENIGN]
BOOTSTRAP_SEED = 20261016  # fixed and logged (§4.3)


@dataclass(frozen=True)
class BundleMeta:
    family: str  # ground-truth label
    sources: frozenset[str]  # sources present in the bundle
    episode_id: str  # "" for benign
    honeypot_keyed: bool


def load_bundle_meta(path: Path = EVAL_BUNDLES) -> dict[str, BundleMeta]:
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    meta: dict[str, BundleMeta] = {}
    for row in pq.read_table(path).to_pylist():
        sources = frozenset(str(s) for s in row["sources"])
        meta[str(row["bundle_id"])] = BundleMeta(
            family=str(row["label"]),
            sources=sources,
            episode_id=str(row["episode_id"] or ""),
            honeypot_keyed="honeypot" in sources,
        )
    return meta


def _detected_attack(row: Mapping[str, object]) -> float:
    pred = _pred(row)
    return 1.0 if (pred is not None and pred != BENIGN) else 0.0


def _classified_right(row: Mapping[str, object]) -> float:
    return 1.0 if _pred(row) == _truth(row) else 0.0


def _per_bundle_majority(
    rows: Iterable[Mapping[str, object]], score: Callable[[Mapping[str, object]], float]
) -> dict[str, float]:
    """Majority (for a 0/1 score, the rounded mean) over each bundle's k repetitions."""
    by_bundle: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_bundle[str(row["bundle_id"])].append(score(row))
    return {b: (1.0 if sum(v) > len(v) / 2 else 0.0) for b, v in by_bundle.items()}


@dataclass(frozen=True)
class Cell:
    condition: str  # C1..C7
    family: str
    n: int
    recall: float  # detection recall (fraction detected as attack)
    recall_lo: float
    recall_hi: float
    accuracy: float  # classification accuracy (fraction classified as the right family)
    accuracy_lo: float
    accuracy_hi: float


def _ci(values: dict[str, float], episode_of: Mapping[str, str]) -> tuple[float, float, float]:
    """Point estimate and the 95% episode-bootstrap interval of the mean of per-bundle values."""
    bundles = sorted(values)
    if not bundles:
        return 0.0, 0.0, 0.0
    blocks = blocks_from_episodes(
        [episode_of.get(b, "") for b in bundles], [values[b] for b in bundles]
    )
    ci = block_bootstrap_ci(blocks, seed=BOOTSTRAP_SEED)
    return ci.estimate, ci.lo, ci.hi


def stratified_cells(
    rows: Iterable[Mapping[str, object]],
    conditions: Sequence[ExperimentConfig],
    meta: Mapping[str, BundleMeta],
) -> list[Cell]:
    """One cell per (condition, family): recall and accuracy with episode-bootstrap intervals."""
    labels = {config_hash(c): f"C{i + 1}" for i, c in enumerate(conditions)}
    by_cond: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        by_cond[str(row["config_hash"])].append(row)
    episode_of = {b: m.episode_id for b, m in meta.items()}

    cells: list[Cell] = []
    for cfg_hash, label in sorted(labels.items(), key=lambda kv: kv[1]):
        cond_rows = by_cond.get(cfg_hash, [])
        for family in FAMILIES:
            fam_rows = [
                r for r in cond_rows if meta.get(str(r["bundle_id"]), _MISSING).family == family
            ]
            if not fam_rows:
                continue
            recall = _per_bundle_majority(fam_rows, _detected_attack)
            accuracy = _per_bundle_majority(fam_rows, _classified_right)
            r_est, r_lo, r_hi = _ci(recall, episode_of)
            a_est, a_lo, a_hi = _ci(accuracy, episode_of)
            cells.append(
                Cell(
                    label,
                    family,
                    len(recall),
                    round(r_est, 4),
                    round(r_lo, 4),
                    round(r_hi, 4),
                    round(a_est, 4),
                    round(a_lo, 4),
                    round(a_hi, 4),
                )
            )
    return cells


_MISSING = BundleMeta(family="", sources=frozenset(), episode_id="", honeypot_keyed=False)


def fusion_gain(cells: Sequence[Cell]) -> dict[str, dict[str, float]]:
    """Per family: C1 minus the best single source (C2/C3/C4) on recall and accuracy."""
    singles = {"C2", "C3", "C4"}
    out: dict[str, dict[str, float]] = {}
    for family in FAMILIES:
        fam = {c.condition: c for c in cells if c.family == family}
        if "C1" not in fam:
            continue
        best_recall = max((fam[s].recall for s in singles if s in fam), default=0.0)
        best_acc = max((fam[s].accuracy for s in singles if s in fam), default=0.0)
        out[family] = {
            "recall_gain": round(fam["C1"].recall - best_recall, 4),
            "accuracy_gain": round(fam["C1"].accuracy - best_acc, 4),
        }
    return out


def _bundle_outcome(
    rows: Iterable[Mapping[str, object]], score: Callable[[Mapping[str, object]], float]
) -> dict[str, dict[str, bool]]:
    """Per condition: majority-over-k boolean outcome per bundle."""
    by_cond: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        by_cond[str(row["config_hash"])].append(row)
    return {
        h: {b: v >= 0.5 for b, v in _per_bundle_majority(rs, score).items()}
        for h, rs in by_cond.items()
    }


@dataclass(frozen=True)
class H1Test:
    contrast: str  # "C1 vs C2" etc.
    outcome: str  # DET | CLS
    beats: bool  # C1 strictly better on the point estimate
    statistic: float
    p_value: float


def h1_tests(
    rows: Iterable[Mapping[str, object]],
    conditions: Sequence[ExperimentConfig],
    meta: Mapping[str, BundleMeta],
    *,
    honeypot_keyed: bool | None = None,
) -> list[H1Test]:
    """C1 vs each single source on DET and CLS (paired McNemar). `honeypot_keyed` filters bundles:
    None keeps all, True only honeypot-keyed, False excludes them."""
    labels = {config_hash(c): f"C{i + 1}" for i, c in enumerate(conditions)}
    inv = {v: k for k, v in labels.items()}
    kept = [
        r
        for r in rows
        if honeypot_keyed is None
        or meta.get(str(r["bundle_id"]), _MISSING).honeypot_keyed == honeypot_keyed
    ]
    results: list[H1Test] = []
    for outcome, score in (("DET", _detected_attack), ("CLS", _classified_right)):
        outcomes = _bundle_outcome(kept, score)
        c1 = outcomes.get(inv["C1"], {})
        for single in ("C2", "C3", "C4"):
            if single not in inv:
                continue
            cs = outcomes.get(inv[single], {})
            bundles = sorted(set(c1) & set(cs))
            a, b = [c1[x] for x in bundles], [cs[x] for x in bundles]
            stat, p = mcnemar(a, b)
            beats = sum(a) > sum(b)
            results.append(H1Test(f"C1 vs {single}", outcome, beats, round(stat, 4), round(p, 4)))
    return results


def write_stratified_csv(cells: Sequence[Cell], path: Path = STRATIFIED_CSV) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "condition",
                "family",
                "n",
                "recall",
                "recall_lo",
                "recall_hi",
                "accuracy",
                "accuracy_lo",
                "accuracy_hi",
            ]
        )
        for c in cells:
            writer.writerow(
                [
                    c.condition,
                    c.family,
                    c.n,
                    c.recall,
                    c.recall_lo,
                    c.recall_hi,
                    c.accuracy,
                    c.accuracy_lo,
                    c.accuracy_hi,
                ]
            )


def _test_lines(tests: Sequence[H1Test]) -> list[str]:
    out = ["| Contrast | Outcome | C1 better? | McNemar | p |", "|---|---|---|---|---|"]
    for t in tests:
        better = "yes" if t.beats else "no"
        out.append(f"| {t.contrast} | {t.outcome} | {better} | {t.statistic} | {t.p_value} |")
    return out


def write_analysis_md(
    cells: Sequence[Cell],
    gain: Mapping[str, Mapping[str, float]],
    tests_all: Sequence[H1Test],
    tests_no_hp: Sequence[H1Test],
    tests_hp: Sequence[H1Test],
    path: Path = ANALYSIS_MD,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# H1 stratified analysis (E9-10, SCRUM-115)",
        "",
        "GENERATED by `python -m thesis.eval.h1`. H1: the all-sources agent (C1) beats each single",
        "source (C2 flows, C3 mqtt, C4 honeypot) on detection (DET) and classification (CLS).",
        "Bundle level, majority over k; episode-bootstrap 95% intervals (§4.3). Per-family",
        "cells are in `results/h1_stratified.csv`.",
        "",
        "## Visibility: all sources (C1, 3 sources) vs each single source (1 source)",
        "",
        *_test_lines(tests_all),
        "",
        "Visibility groups in this matrix are 3 sources (C1) and 1 source (C2/C3/C4); there is",
        "no 2-source condition. H1 holds for a contrast only when C1 is better and the paired",
        "test and the bootstrap interval of the difference agree (§4.3, per the stats report).",
        "",
        "## Gain from fusion (C1 minus the best single source), per family",
        "",
        "| Family | Recall gain | Accuracy gain |",
        "|---|---|---|",
        *(f"| {fam} | {g['recall_gain']} | {g['accuracy_gain']} |" for fam, g in gain.items()),
        "",
        "## With and without honeypot-keyed bundles",
        "",
        "No benign traffic reaches the honeypot (§8), so honeypot-keyed bundles are all attacks",
        "and inflate detection for any condition that sees the honeypot. H1 is reported both ways.",
        "",
        "### Excluding honeypot-keyed bundles",
        "",
        *_test_lines(tests_no_hp),
        "",
        "### Only honeypot-keyed bundles",
        "",
        *_test_lines(tests_hp),
        "",
    ]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def main() -> int:  # pragma: no cover - reads the frozen results
    import pyarrow.parquet as pq

    from thesis.eval.run import load_conditions

    # The primary (unstratified) H1 significance test lives in E9-05 (`thesis.eval.stats`); this
    # module adds the per-family and honeypot-split view the ticket asks for.
    if not RESULTS_PARQUET.exists():
        print(f"no results at {RESULTS_PARQUET}; run E9-09 first")
        return 2
    rows = pq.read_table(RESULTS_PARQUET).to_pylist()
    meta = load_bundle_meta()
    from thesis.config import Provenance

    prov = Provenance(
        model="results",
        model_revision="results",
        provider="results",
        temperature=0.6,
        top_p=0.9,
        max_tokens=768,
        seed=None,
        prompt_template_version="prompts-v1.1",
        graph_version="graph-v1.0",
    )
    conditions = load_conditions(prov)
    cells = stratified_cells(rows, conditions, meta)
    write_stratified_csv(cells)
    write_analysis_md(
        cells,
        fusion_gain(cells),
        h1_tests(rows, conditions, meta),
        h1_tests(rows, conditions, meta, honeypot_keyed=False),
        h1_tests(rows, conditions, meta, honeypot_keyed=True),
    )
    print(f"wrote {STRATIFIED_CSV} and {ANALYSIS_MD}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "BundleMeta",
    "Cell",
    "H1Test",
    "fusion_gain",
    "h1_tests",
    "load_bundle_meta",
    "stratified_cells",
    "write_analysis_md",
    "write_stratified_csv",
]
